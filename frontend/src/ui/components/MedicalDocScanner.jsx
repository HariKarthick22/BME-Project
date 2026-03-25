import { useState, useRef } from 'react';
import {
  extractDiagnosis,
  extractMedications,
  extractProcedures,
  getMedicalCodingSummary
} from '../utils/medicalCoding';
import './MedicalDocScanner.css';

/**
 * Medical Document Scanner Component
 * Handles prescription/medical document uploads with OCR and NER
 */
export default function MedicalDocScanner({ onDataExtracted }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [extracted, setExtracted] = useState(null);
  const [error, setError] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef(null);

  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
  const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'application/pdf'];

  /**
   * Handle file selection
   */
  const handleFileSelect = (e) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    // Validate file
    if (!ACCEPTED_TYPES.includes(selectedFile.type)) {
      setError('Please upload a valid image or PDF. Accepted: JPG, PNG, PDF');
      return;
    }

    if (selectedFile.size > MAX_FILE_SIZE) {
      setError('File size exceeds 10MB limit');
      return;
    }

    setFile(selectedFile);
    setError(null);

    // Create preview for images
    if (selectedFile.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target.result);
      reader.readAsDataURL(selectedFile);
    } else {
      setPreview(null);
    }
  };

  /**
   * Handle drag and drop
   */
  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.add('drag-active');
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-active');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove('drag-active');

    const droppedFile = e.dataTransfer?.files?.[0];
    if (droppedFile) {
      handleFileSelect({ target: { files: [droppedFile] } });
    }
  };

  /**
   * Upload and process document
   */
  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    setLoading(true);
    setError(null);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Simulate progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 30, 90));
      }, 500);

      const response = await fetch('/api/parse-prescription', {
        method: 'POST',
        body: formData
      });

      clearInterval(progressInterval);

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
      }

      const result = await response.json();
      setUploadProgress(100);

      // Process extracted data
      const processedData = {
        text: result.summary || file.name,
        diagnoses: result.extraction?.diagnosis || [],
        medications: result.extraction?.medications || [],
        procedures: result.extraction?.procedure || [],
        raw: result
      };

      setExtracted(processedData);

      // Additional local extraction for missing data
      if (processedData.diagnoses.length === 0 && result.summary) {
        processedData.diagnoses = extractDiagnosis(result.summary);
      }
      if (processedData.medications.length === 0 && result.summary) {
        processedData.medications = extractMedications(result.summary);
      }
      if (processedData.procedures.length === 0 && result.summary) {
        processedData.procedures = extractProcedures(result.summary);
      }

      // Callback with extracted data
      if (onDataExtracted) {
        const summary = getMedicalCodingSummary(processedData);
        onDataExtracted(summary);
      }

      // Reset after 2 seconds
      setTimeout(() => {
        setUploadProgress(0);
      }, 2000);
    } catch (err) {
      setError(err.message || 'Failed to process document');
      setUploadProgress(0);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Reset form
   */
  const handleReset = () => {
    setFile(null);
    setPreview(null);
    setExtracted(null);
    setError(null);
    setUploadProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="medical-doc-scanner">
      <div className="scanner-header">
        <h2>📄 Medical Document Scanner</h2>
        <p>Upload prescription, medical reports, or diagnosis documents for automatic processing</p>
      </div>

      {/* File Upload Area */}
      {!extracted ? (
        <div className="upload-section">
          <div
            className="upload-dropzone"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_TYPES.join(',')}
              onChange={handleFileSelect}
              hidden
            />

            {preview ? (
              <div className="preview-container">
                <img src={preview} alt="Document preview" className="preview-image" />
                <p className="file-name">{file?.name}</p>
              </div>
            ) : (
              <>
                <div className="upload-icon">📤</div>
                <h3>Drag and drop your medical document</h3>
                <p>or click to select from your device</p>
                <p className="file-types">Supported: JPG, PNG, PDF (max 10MB)</p>
              </>
            )}
          </div>

          {error && <div className="error-message">{error}</div>}

          {file && (
            <div className="upload-controls">
              <button
                className="btn-primary"
                onClick={handleUpload}
                disabled={loading}
              >
                {loading ? `Processing... ${uploadProgress}%` : 'Process Document'}
              </button>
              <button
                className="btn-secondary"
                onClick={handleReset}
                disabled={loading}
              >
                Clear
              </button>
            </div>
          )}

          {uploadProgress > 0 && uploadProgress < 100 && (
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${uploadProgress}%` }}></div>
            </div>
          )}
        </div>
      ) : (
        /* Extracted Data Display */
        <div className="extracted-section">
          <div className="extracted-header">
            <h3>✅ Document Processed Successfully</h3>
            <button className="btn-secondary" onClick={handleReset}>
              Upload Another
            </button>
          </div>

          {/* Diagnoses */}
          {extracted.diagnoses?.length > 0 && (
            <div className="extracted-card">
              <h4>🩺 Diagnosed Conditions</h4>
              <div className="items-list">
                {extracted.diagnoses.map((diagnosis, idx) => (
                  <div key={idx} className="item">
                    <span className="item-name">{diagnosis.text || diagnosis}</span>
                    {diagnosis.code && (
                      <span className="item-code">ICD-10: {diagnosis.code}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Medications */}
          {extracted.medications?.length > 0 && (
            <div className="extracted-card">
              <h4>💊 Medications</h4>
              <div className="items-list">
                {extracted.medications.map((med, idx) => (
                  <div key={idx} className="item">
                    <span className="item-name">{med.name || med}</span>
                    {med.strength && (
                      <span className="item-detail">{med.strength}</span>
                    )}
                    {med.frequency && (
                      <span className="item-detail">{med.frequency}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Procedures */}
          {extracted.procedures?.length > 0 && (
            <div className="extracted-card">
              <h4>🏥 Procedures/Treatments</h4>
              <div className="items-list">
                {extracted.procedures.map((proc, idx) => (
                  <div key={idx} className="item">
                    <span className="item-name">{proc.description || proc}</span>
                    {proc.code && (
                      <span className="item-code">Code: {proc.code}</span>
                    )}
                    {proc.specialty && (
                      <span className="item-detail">Specialty: {proc.specialty}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {!extracted.diagnoses?.length &&
            !extracted.medications?.length &&
            !extracted.procedures?.length && (
              <div className="no-data-message">
                <p>No medical data was extracted from the document.</p>
                <p>Try uploading a clearer image or different document.</p>
              </div>
            )}
        </div>
      )}
    </div>
  );
}
