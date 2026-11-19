import Icon from "../../components/ui/Icon";
import Button from "../../components/ui/Button";
import Spinner from "../../components/ui/Spinner";
import ImageProcessingDisclosure from "../../components/ImageProcessingDisclosure";

export default function LabelUploadForm({
  fileInputRef,
  selectedImage,
  previewUrl,
  uploadError,
  isUploading,
  onSelectImage,
  onSubmit,
}) {
  return (
    <section className="upload-layout" aria-label="Label image extraction">
      <form className="analysis-card upload-card" onSubmit={onSubmit}>
        <div className="card-heading">
          <div>
            <p className="step-label">STEP 1 · UPLOAD</p>
            <h2>Choose a label image</h2>
          </div>
          <span className="optional-label">JPG · JPEG · PNG · WEBP</span>
        </div>

        <input
          ref={fileInputRef}
          className="visually-hidden"
          type="file"
          accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
          onChange={(event) => {
            onSelectImage(event.target.files?.[0]);
            event.currentTarget.value = "";
          }}
        />
        {selectedImage ? (
          <div className="selected-image">
            <img src={previewUrl} alt="Selected nutrition label preview" />
            <div className="selected-image-info">
              <strong>{selectedImage.name}</strong>
              <span>
                {(selectedImage.size / (1024 * 1024)).toFixed(2)} MiB · Ready
                to extract
              </span>
              <button
                className="text-button"
                type="button"
                onClick={() => fileInputRef.current?.click()}
              >
                Replace image
              </button>
            </div>
          </div>
        ) : (
          <div
            className="dropzone"
            role="region"
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              onSelectImage(event.dataTransfer.files?.[0]);
            }}
            aria-label="Drop a food label photo"
          >
            <span className="upload-icon" aria-hidden="true">
              <svg viewBox="0 0 48 48" fill="none">
                <path
                  d="M24 31V10m0 0-8 8m8-8 8 8"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M11 29v7a3 3 0 0 0 3 3h20a3 3 0 0 0 3-3v-7"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
              </svg>
            </span>
            <strong>Drag &amp; Drop Food Label Photo Here</strong>
            <span>Supported formats: JPG, JPEG, PNG, WEBP</span>
            <small>Maximum file size: 15 MB</small>
            <Button
              type="button"
              className="browse-files-button"
              onClick={() => fileInputRef.current?.click()}
            >
              Browse Files
            </Button>
          </div>
        )}

        {uploadError && (
          <p className="form-error" role="alert">
            <span aria-hidden="true">!</span>
            {uploadError}
          </p>
        )}

        <Button
          type="submit"
          disabled={!selectedImage || isUploading}
        >
          {isUploading ? (
            <>
              <Spinner />
              Reading label…
            </>
          ) : (
            <>
              Analyze Food Label
              <span aria-hidden="true">→</span>
            </>
          )}
        </Button>
        <ImageProcessingDisclosure />
      </form>

      <aside className="upload-note">
        <span className="note-icon" aria-hidden="true">
          <Icon name="sparkle" size={18} />
        </span>
        <p className="step-label">A NOTE ON EXTRACTION</p>
        <h2>Check every value.</h2>
        <p>
          Text recognition can misread small print, columns, or colors.
          Extracted details are suggestions for your review, not verified
          label data.
        </p>
        <div className="review-legend">
          <span className="review-dot" aria-hidden="true" />
          <span>Every extracted field needs your review</span>
        </div>
      </aside>
    </section>
  );
}
