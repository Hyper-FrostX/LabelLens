import { useEffect, useRef, useState } from "react";

import LabelReviewForm from "./LabelReviewForm";
import LabelUploadForm from "./LabelUploadForm";
import NutritionInputForm from "./NutritionInputForm";
import NutritionReport from "./NutritionReport";
import AccountPanel from "./AccountPanel";
import ProductAnalysisSections from "./ProductAnalysisSections";
import ProductQuestionAnswer from "./ProductQuestionAnswer";
import {
  getApiErrorMessage,
  isAcceptedImage,
  additionalNutrientFields,
  nutrientFields,
  prepareReviewData,
} from "./nutritionUtils";
import {
  buildLabelCorrections,
  buildProductAnalysisPayload,
  isRouteUnavailableStatus,
  normalizeProductAnalysisResponse,
  toLegacyLabelPayload,
} from "./productAnalysisUtils";

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
const EMPTY_ADDITIONAL_NUTRIENTS = Object.fromEntries(
  additionalNutrientFields.map(({ name, unit }) => [
    name,
    { value: "", unit },
  ])
);

export default function NutritionWorkspace({ focusSection = "scan" }) {
  const [selectedImage, setSelectedImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [extraction, setExtraction] = useState(null);
  const [review, setReview] = useState(null);
  const [uploadError, setUploadError] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [analysisValues, setAnalysisValues] = useState(EMPTY_NUTRIENTS);
  const [analysisAdditionalNutrients, setAnalysisAdditionalNutrients] =
    useState(EMPTY_ADDITIONAL_NUTRIENTS);
  const [analysisBasis, setAnalysisBasis] = useState("");
  const [recommendationGoal, setRecommendationGoal] = useState("balanced");
  const [analysisServingSize, setAnalysisServingSize] = useState("");
  const [analysisProductName, setAnalysisProductName] = useState("");
  const [analysisIngredientsText, setAnalysisIngredientsText] = useState("");
  const [analysisMayContainText, setAnalysisMayContainText] = useState("");
  const [analysisDeclaredAllergenText, setAnalysisDeclaredAllergenText] = useState("");
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisError, setAnalysisError] = useState("");
  const [confirmedLabel, setConfirmedLabel] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [explanationLevel, setExplanationLevel] = useState("beginner");
  const [analysisContext, setAnalysisContext] = useState(null);
  const [usedLegacyAnalysis, setUsedLegacyAnalysis] = useState(false);
  const [accessToken, setAccessToken] = useState("");
  const [saveToHistory, setSaveToHistory] = useState(false);
  const [historyVersion, setHistoryVersion] = useState(0);

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

  function updateRecommendationGoal(value) {
    setRecommendationGoal(value);
    invalidateAnalysis();
  }

  function invalidateAnalysis() {
    analysisRequestIdRef.current += 1;
    setAnalysisResult(null);
    setAnalysisError("");
    setIsAnalyzing(false);
    setAnalysisContext(null);
    setUsedLegacyAnalysis(false);
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

  function updateOtherField(name, value) {
    setIsConfirmed(false);
    setConfirmedLabel(null);
    invalidateAnalysis();
    setReview((current) => ({
      ...current,
      otherFields: { ...current.otherFields, [name]: value },
    }));
  }

  function updateSymbolReview(value) {
    setIsConfirmed(false);
    setConfirmedLabel(null);
    invalidateAnalysis();
    setReview((current) => ({ ...current, symbolReview: value }));
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
    setAnalysisAdditionalNutrients(review.additionalNutrients);
    setAnalysisBasis(review.basis);
    setAnalysisServingSize(review.servingSize);
    setAnalysisProductName(review.productName);
    setAnalysisIngredientsText(review.ingredientsText);
    setAnalysisMayContainText(review.mayContainText);
    setAnalysisDeclaredAllergenText(review.declaredAllergenText);
    const snapshot = {
      nutrients: nextValues,
      additionalNutrients: review.additionalNutrients,
      basis: review.basis,
      servingSize: review.servingSize,
      productName: review.productName,
      ingredientsText: review.ingredientsText,
      mayContainText: review.mayContainText,
      declaredAllergenText: review.declaredAllergenText,
      otherFields: review.otherFields,
      symbolReview: review.symbolReview,
      labelCorrections: buildLabelCorrections({
        ...review,
        nutrients: nextValues,
      }),
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

    let payload;
    try {
      payload = buildProductAnalysisPayload({
        productName: valuesSnapshot?.productName ?? analysisProductName,
        declaredAllergenText:
          valuesSnapshot?.declaredAllergenText ?? analysisDeclaredAllergenText,
        ingredientsText: valuesSnapshot?.ingredientsText ?? analysisIngredientsText,
        mayContainText: valuesSnapshot?.mayContainText ?? analysisMayContainText,
        nutrients: valuesSnapshot?.nutrients ?? analysisValues,
        additionalNutrients:
          valuesSnapshot?.additionalNutrients ?? analysisAdditionalNutrients,
        basis: valuesSnapshot?.basis ?? analysisBasis,
        recommendationGoal,
        servingSize: valuesSnapshot?.servingSize ?? analysisServingSize,
        explanationLevel,
        saveToHistory,
        labelText: extraction?.ocr_text ?? "",
        labelCorrections: valuesSnapshot?.labelCorrections ?? {},
        correctionsConfirmed: Boolean(extraction && valuesSnapshot),
        extractionMetadata: extraction
          ? {
              fields: (extraction.fields ?? []).slice(0, 100).map((field) => ({
                field_name: field.field_name,
                field_type: field.field_type,
                confidence_state: field.confidence_state,
                ocr_confidence: field.ocr_confidence,
                processing_method: field.processing_method,
                review_status: field.review_status,
                source_region: field.source_region
                  ? {
                      region_type: field.source_region.region_type,
                      source_coordinates: field.source_region.source_coordinates,
                    }
                  : null,
              })),
              regions: (extraction.regions ?? []).slice(0, 20).map((region) => ({
                region_type: region.region_type,
                source_coordinates: region.source_coordinates,
                processing_method: region.processing_method,
                confidence_state: region.confidence_state,
              })),
              processing: extraction.processing ?? null,
              ocr_quality: extraction.ocr_quality ?? null,
              symbol_detection: extraction.symbol_detection ?? null,
            }
          : null,
        symbolReview: valuesSnapshot?.symbolReview ?? null,
      });
    } catch (error) {
      setAnalysisError(error.message);
      return;
    }

    setIsAnalyzing(true);
    try {
      const response = await fetch(`${API_BASE_URL}/analyze/product`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify(payload),
      });
      let responseData = null;
      try {
        responseData = await response.json();
      } catch {
        if (response.ok || !isRouteUnavailableStatus(response.status)) {
          throw new Error(response.ok
            ? "The backend returned an unreadable response."
            : `The product analysis request failed (HTTP ${response.status}).`);
        }
      }
      if (response.ok) {
        if (!responseData || typeof responseData !== "object") {
          throw new Error("The backend returned an invalid product analysis response.");
        }
        if (analysisRequestIdRef.current === requestId) {
          const normalizedResult = normalizeProductAnalysisResponse(responseData);
          setAnalysisResult(normalizedResult);
          setAnalysisContext({ ...payload, ...normalizedResult });
          if (normalizedResult.saved_scan_id) {
            setHistoryVersion((current) => current + 1);
          }
        }
      } else if (isRouteUnavailableStatus(response.status)) {
        const legacyResponse = await fetch(`${API_BASE_URL}/analyze/label`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(toLegacyLabelPayload(payload)),
        });
        let legacyData;
        try {
          legacyData = await legacyResponse.json();
        } catch {
          throw new Error(legacyResponse.ok
            ? "The backend returned an unreadable legacy analysis response."
            : `Label analysis failed (HTTP ${legacyResponse.status}).`);
        }
        if (!legacyResponse.ok) {
          throw new Error(
            getApiErrorMessage(legacyData, legacyResponse.status, "Label analysis")
          );
        }
        if (analysisRequestIdRef.current === requestId) {
          const legacyResult = normalizeProductAnalysisResponse({
            ...legacyData,
            nutrition_analysis: legacyData,
            product_overview: null,
            additive_analysis: legacyData.additive_analysis ?? null,
            allergen_analysis: null,
            personalized_suitability: null,
            alternatives: null,
            limitations: null,
          });
          setAnalysisResult(legacyResult);
          setAnalysisContext({ ...payload, ...legacyResult });
          setUsedLegacyAnalysis(true);
        }
      } else {
        throw new Error(
          getApiErrorMessage(responseData, response.status, "Product analysis")
        );
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

  function updateAnalysisAdditionalNutrient(name, value) {
    setAnalysisAdditionalNutrients((current) => ({
      ...current,
      [name]: { ...current[name], value },
    }));
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

  function updateAnalysisProductName(value) {
    setAnalysisProductName(value);
    invalidateAnalysis();
  }

  function updateAnalysisIngredientsText(value) {
    setAnalysisIngredientsText(value);
    invalidateAnalysis();
  }

  function updateAnalysisMayContainText(value) {
    setAnalysisMayContainText(value);
    invalidateAnalysis();
  }

  function updateAnalysisDeclaredAllergenText(value) {
    setAnalysisDeclaredAllergenText(value);
    invalidateAnalysis();
  }

  function updateExplanationLevel(event) {
    setExplanationLevel(event.target.value);
  }

  return (
    <>
      <AccountPanel
        apiBaseUrl={API_BASE_URL}
        accessToken={accessToken}
        onAuthChange={setAccessToken}
        historyVersion={historyVersion}
        onExpertiseChange={setExplanationLevel}
        defaultOpen={focusSection === "history" || focusSection === "profile"}
      />
      {focusSection === "alternatives" && !analysisResult && (
        <p className="legacy-api-notice" role="status">
          Analyze a label with at least two comparable per-100 g or per-100 ml
          nutrient values. Potential alternatives are drawn only from stored
          product data and may be unavailable.
        </p>
      )}
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
          previewUrl={previewUrl}
          isConfirmed={isConfirmed}
          isAnalyzing={isAnalyzing}
          analysisError={analysisError}
          onUpdateReview={updateReview}
          onUpdateOtherField={updateOtherField}
          onUpdateSymbolReview={updateSymbolReview}
          onUpdateNutrient={updateNutrient}
          onUpdateAdditionalNutrient={(name, value) => {
            setIsConfirmed(false);
            setConfirmedLabel(null);
            invalidateAnalysis();
            setReview((current) => ({
              ...current,
              additionalNutrients: {
                ...current.additionalNutrients,
                [name]: { ...current.additionalNutrients[name], value },
              },
            }));
          }}
          onConfirm={confirmReview}
        />
      )}

      <NutritionInputForm
        isConfirmed={isConfirmed}
        extraction={extraction}
        confirmedLabel={confirmedLabel}
        analysisBasis={analysisBasis}
        recommendationGoal={recommendationGoal}
        analysisServingSize={analysisServingSize}
        analysisValues={analysisValues}
        analysisAdditionalNutrients={analysisAdditionalNutrients}
        analysisProductName={analysisProductName}
        analysisIngredientsText={analysisIngredientsText}
        analysisMayContainText={analysisMayContainText}
        analysisDeclaredAllergenText={analysisDeclaredAllergenText}
        saveToHistory={saveToHistory}
        accessToken={accessToken}
        analysisError={analysisError}
        isAnalyzing={isAnalyzing}
        onSubmit={submitAnalysis}
        onBasisChange={updateAnalysisBasis}
        onRecommendationGoalChange={updateRecommendationGoal}
        onServingSizeChange={updateAnalysisServingSize}
        onProductNameChange={updateAnalysisProductName}
        onIngredientsTextChange={updateAnalysisIngredientsText}
        onMayContainTextChange={updateAnalysisMayContainText}
        onDeclaredAllergenTextChange={updateAnalysisDeclaredAllergenText}
        onSaveToHistoryChange={setSaveToHistory}
        onValueChange={updateAnalysisValue}
        onAdditionalNutrientChange={updateAnalysisAdditionalNutrient}
      />

      {analysisResult && (
        <>
          <div className="analysis-display-toggle" role="group" aria-label="Explanation detail">
            <span>Explanation level</span>
            <label>
              <input
                type="radio"
                name="explanation-level"
                value="beginner"
                checked={explanationLevel === "beginner"}
                onChange={updateExplanationLevel}
              />
              Beginner
            </label>
            <label>
              <input
                type="radio"
                name="explanation-level"
                value="expert"
                checked={explanationLevel === "expert"}
                onChange={updateExplanationLevel}
              />
              Expert
            </label>
            <p>This changes explanation detail only; it does not rescan or reanalyze the label.</p>
          </div>
          {usedLegacyAnalysis && (
            <p className="legacy-api-notice" role="status">
              This backend does not yet provide the product analysis route. Showing available label nutrition results; product, additive, allergen, suitability, alternative, and limitation data not returned by the backend are marked unavailable.
            </p>
          )}
          <NutritionReport
            analysisResult={analysisResult}
            resultSectionRef={resultSectionRef}
            expertMode={explanationLevel === "expert"}
          />
          <ProductAnalysisSections
            analysisResult={analysisResult}
            expertMode={explanationLevel === "expert"}
          />
          {analysisContext && (
            <ProductQuestionAnswer
              apiBaseUrl={API_BASE_URL}
              productContext={analysisContext}
              explanationLevel={explanationLevel}
              accessToken={accessToken}
            />
          )}
        </>
      )}
    </>
  );
}
