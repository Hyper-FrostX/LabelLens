import { useEffect, useRef, useState } from "react";

import LabelReviewForm from "./LabelReviewForm";
import LabelUploadForm from "./LabelUploadForm";
import NutritionInputForm from "./NutritionInputForm";
import NutritionReport from "./NutritionReport";
import {
  getApiErrorMessage,
  isAcceptedImage,
  nutrientFields,
  nutrientUnitFields,
  prepareReviewData,
} from "./nutritionUtils";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");
const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const EMPTY_NUTRIENTS = {
  sugar_g: "",
  added_sugar_g: "",
  sodium_mg: "",
  saturated_fat_g: "",
};

export default function NutritionWorkspace() {
  const [selectedImage, setSelectedImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [extraction, setExtraction] = useState(null);
  const [review, setReview] = useState(null);
  const [uploadError, setUploadError] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [analysisValues, setAnalysisValues] = useState(EMPTY_NUTRIENTS);
  const [analysisBasis, setAnalysisBasis] = useState("");
  const [analysisServingSize, setAnalysisServingSize] = useState("");
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisError, setAnalysisError] = useState("");
  const [confirmedLabel, setConfirmedLabel] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const fileInputRef = useRef(null);
  const previewUrlRef = useRef("");
  const resultSectionRef = useRef(null);
  const analysisRequestIdRef = useRef(0);

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    };
  }, []);

  useEffect(() => {
    if (!analysisResult) return;
    resultSectionRef.current?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
      block: "start",
    });
  }, [analysisResult]);

  function setImagePreview(file) {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = "";
    }
    setSelectedImage(file);
    if (file) {
      const imageUrl = URL.createObjectURL(file);
      previewUrlRef.current = imageUrl;
      setPreviewUrl(imageUrl);
    } else {
      setPreviewUrl("");
    }
  }

  function invalidateAnalysis() {
    analysisRequestIdRef.current += 1;
    setAnalysisResult(null);
    setAnalysisError("");
    setIsAnalyzing(false);
  }

  function selectImage(file) {
    setUploadError("");
    setExtraction(null);
    setReview(null);
    setIsConfirmed(false);
    invalidateAnalysis();
    setConfirmedLabel(null);

    if (!file) return;
    if (!isAcceptedImage(file)) {
      setImagePreview(null);
      setUploadError("Choose a JPEG, PNG, or WebP image.");
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setImagePreview(null);
      setUploadError("Image must be 10 MiB or smaller.");
      return;
    }

    setImagePreview(file);
  }

  async function extractLabel(event) {
    event.preventDefault();
    if (!selectedImage || isUploading) return;

    setUploadError("");
    setExtraction(null);
    setReview(null);
    setIsConfirmed(false);
    setConfirmedLabel(null);
    invalidateAnalysis();
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", selectedImage);
      const response = await fetch(`${API_BASE_URL}/extract/label`, {
        method: "POST",
        body: formData,
      });

      let responseData;
      try {
        responseData = await response.json();
      } catch {
        throw new Error(
          response.ok
            ? "The backend returned an unreadable response."
            : `Label extraction failed (HTTP ${response.status}).`
        );
      }

      if (!response.ok) {
        throw new Error(getApiErrorMessage(responseData, response.status));
      }
      if (!responseData || typeof responseData !== "object") {
        throw new Error("The backend returned an invalid extraction response.");
      }

      setExtraction(responseData);
      setReview(prepareReviewData(responseData));
    } catch (error) {
      setUploadError(
        error instanceof TypeError
          ? `Could not connect to the Label Lens API at ${API_BASE_URL}. Check that the backend is running and the API URL is correct.`
          : error.message
      );
    } finally {
      setIsUploading(false);
    }
  }

  function updateReview(field, value) {
    setIsConfirmed(false);
    setConfirmedLabel(null);
    invalidateAnalysis();
    setReview((current) => ({ ...current, [field]: value }));
  }

  function updateNutrient(name, value) {
    setIsConfirmed(false);
    setConfirmedLabel(null);
    invalidateAnalysis();
    setReview((current) => ({
      ...current,
      nutrients: { ...current.nutrients, [name]: value },
    }));
  }

  function confirmReview(event) {
    event.preventDefault();
    const nextValues = { ...review.nutrients };

    for (const field of nutrientFields) {
      if (nextValues[field.name].trim() === "") continue;
      const value = Number(nextValues[field.name]);
      if (!Number.isFinite(value) || value < 0) {
        setUploadError(`${field.label} must be a non-negative number.`);
        setIsConfirmed(false);
        return;
      }
    }

    setUploadError("");
    setAnalysisValues(nextValues);
    setAnalysisBasis(review.basis);
    setAnalysisServingSize(review.servingSize);
    const snapshot = {
      nutrients: nextValues,
      basis: review.basis,
      servingSize: review.servingSize,
      ingredientsText: review.ingredientsText,
    };
    setConfirmedLabel(snapshot);
    setIsConfirmed(true);
    void submitAnalysis(null, snapshot);
  }

  async function submitAnalysis(event, labelSnapshot = null) {
    event?.preventDefault();
    const requestId = ++analysisRequestIdRef.current;
    setAnalysisError("");
    setAnalysisResult(null);
    setIsAnalyzing(false);

    const valuesSnapshot = labelSnapshot ?? confirmedLabel;
    if (extraction && !valuesSnapshot) {
      setAnalysisError(
        "Review and confirm the extracted label details before analyzing them."
      );
      return;
    }

    const valuesToAnalyze = valuesSnapshot?.nutrients ?? analysisValues;
    const payload = {
      basis: (valuesSnapshot?.basis ?? analysisBasis) || null,
      serving_size_text:
        (valuesSnapshot?.servingSize ?? analysisServingSize).trim() || null,
      ingredients_text:
        valuesSnapshot?.ingredientsText.trim() || null,
    };
    for (const field of nutrientFields) {
      const rawValue = valuesToAnalyze[field.name].trim();
      payload[nutrientUnitFields[field.name]] = field.unit;
      if (rawValue === "") {
        payload[field.name] = null;
        continue;
      }
      const value = Number(rawValue);
      if (!Number.isFinite(value) || value < 0) {
        setAnalysisError(`${field.label} must be a non-negative number.`);
        return;
      }
      payload[field.name] = value;
    }

    setIsAnalyzing(true);
    try {
      const response = await fetch(`${API_BASE_URL}/analyze/label`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      let responseData;
      try {
        responseData = await response.json();
      } catch {
        throw new Error(
          response.ok
            ? "The backend returned an unreadable response."
            : `The analysis request failed (HTTP ${response.status}).`
        );
      }
      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(responseData, response.status, "Label analysis")
        );
      }
      if (analysisRequestIdRef.current === requestId) {
        setAnalysisResult(responseData);
      }
    } catch (error) {
      if (analysisRequestIdRef.current === requestId) {
        setAnalysisError(
          error instanceof TypeError
            ? `Could not connect to the Label Lens API at ${API_BASE_URL}. Check that the backend is running and the API URL is correct.`
            : error.message
        );
      }
    } finally {
      if (analysisRequestIdRef.current === requestId) {
        setIsAnalyzing(false);
      }
    }
  }

  function updateAnalysisValue(event) {
    const { name, value } = event.target;
    setAnalysisValues((current) => ({ ...current, [name]: value }));
    invalidateAnalysis();
  }

  function updateAnalysisBasis(value) {
    setAnalysisBasis(value);
    invalidateAnalysis();
  }

  function updateAnalysisServingSize(value) {
    setAnalysisServingSize(value);
    invalidateAnalysis();
  }

  return (
    <>
      <LabelUploadForm
        fileInputRef={fileInputRef}
        selectedImage={selectedImage}
        previewUrl={previewUrl}
        uploadError={uploadError}
        isUploading={isUploading}
        onSelectImage={selectImage}
        onSubmit={extractLabel}
      />

      {extraction && review && (
        <LabelReviewForm
          review={review}
          isConfirmed={isConfirmed}
          isAnalyzing={isAnalyzing}
          analysisError={analysisError}
          onUpdateReview={updateReview}
          onUpdateNutrient={updateNutrient}
          onConfirm={confirmReview}
        />
      )}

      <NutritionInputForm
        isConfirmed={isConfirmed}
        extraction={extraction}
        confirmedLabel={confirmedLabel}
        analysisBasis={analysisBasis}
        analysisServingSize={analysisServingSize}
        analysisValues={analysisValues}
        analysisError={analysisError}
        isAnalyzing={isAnalyzing}
        onSubmit={submitAnalysis}
        onBasisChange={updateAnalysisBasis}
        onServingSizeChange={updateAnalysisServingSize}
        onValueChange={updateAnalysisValue}
      />

      {analysisResult && (
        <NutritionReport
          analysisResult={analysisResult}
          resultSectionRef={resultSectionRef}
        />
      )}
    </>
  );
}
