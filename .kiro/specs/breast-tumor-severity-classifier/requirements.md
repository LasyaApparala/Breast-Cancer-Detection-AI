# Requirements Document

## Introduction

A high-accuracy breast tumor severity classification platform that accepts patient details and medical documents (pathology reports, imaging results, lab data) and produces a clinically grounded severity classification. Classification follows a two-step pipeline: Step 1 determines benign vs. malignant; Step 2 applies TNM-based staging (Stage I–IV) only for malignant cases. The system uses the same clinical features that oncologists and validated AI/ML systems rely on: tumor size, shape, margins, lymph node involvement, hormone receptor status (ER/PR), HER2 status, histological grade, and mitotic rate. All outputs must be strictly grounded in the provided input data — strict grounding enforced through rule-based TNM validation, audit trail traceability, and no implicit inference.

---

## Glossary

- **Platform**: The breast tumor severity classification web application described in this document.
- **Classifier**: The ML model pipeline responsible for predicting tumor severity from extracted clinical features. Handles benign/malignant discrimination; staging is delegated to the TNM_Rule_Engine.
- **Document_Parser**: The component that extracts structured clinical features from uploaded documents (PDFs, images, structured forms).
- **Feature_Extractor**: The component that maps parsed document content to the standardized clinical feature set.
- **Severity_Engine**: The component that orchestrates the two-step classification pipeline: running the Classifier for benign/malignant discrimination, then invoking the TNM_Rule_Engine for staging if the result is malignant.
- **TNM_Rule_Engine**: A deterministic rule-based component that maps T (tumor size/extent), N (lymph node involvement), and M (metastasis) values to an AJCC stage (I–IV) according to published AJCC staging tables. Used exclusively for staging malignant cases; benign cases are never passed to this component.
- **Imaging_Model**: A validated convolutional neural network (e.g., EfficientNet-B4) applied to DICOM uploads to perform tumor segmentation and extract imaging-derived Clinical_Features (tumor shape, margin type, density).
- **Calibration_Layer**: A post-hoc calibration component (e.g., temperature scaling) applied to the Classifier's raw output probabilities to ensure the Confidence_Score reflects true empirical probability.
- **Severity_Label**: One of: `Benign`, `Malignant — Stage I`, `Malignant — Stage II`, `Malignant — Stage III`, `Malignant — Stage IV`.
- **Confidence_Score**: A numeric value in [0.0, 1.0] representing the model's certainty in the predicted Severity_Label, after calibration by the Calibration_Layer.
- **Clinical_Features**: The standardized set of oncology-validated input variables: tumor size (mm), tumor shape (regular/irregular), margin type (circumscribed/spiculated/microlobulated/obscured/indistinct), lymph node involvement (count and status), ER status (positive/negative), PR status (positive/negative), HER2 status (positive/negative/equivocal), histological grade (I/II/III), mitotic rate (per 10 HPF), and Ki-67 index (%). Features are grouped into criticality tiers: Tier 1 (tumor size, lymph node involvement, histological grade), Tier 2 (ER status, HER2 status, margin type), Tier 3 (PR status, Ki-67, mitotic rate).
- **Grounded_Output**: An output derived solely from data present in the submitted input; strict grounding enforced through rule-based TNM validation, audit trail traceability, and no implicit inference.
- **Audit_Trail**: A record linking each output field to the specific source document section and extracted value that produced it.
- **User**: A medical professional or authorized operator interacting with the Platform.
- **Admin**: An authorized operator responsible for model management and system configuration.

---

## Requirements

### Requirement 1: Document Upload and Ingestion

**User Story:** As a User, I want to upload patient medical documents in common formats, so that the Platform can extract the clinical data needed for classification.

#### Acceptance Criteria

1. THE Platform SHALL accept document uploads in PDF, JPEG, PNG, TIFF, and DICOM formats.
2. WHEN a document is uploaded, THE Platform SHALL validate that the file format is supported and the file size does not exceed 50 MB per file.
3. IF an uploaded file is in an unsupported format or exceeds the size limit, THEN THE Platform SHALL reject the upload and return a descriptive error message identifying the specific violation.
4. THE Platform SHALL allow a User to upload up to 10 documents per classification request.
5. WHEN a document upload is complete, THE Platform SHALL confirm receipt with a unique document reference ID within 5 seconds.

---

### Requirement 2: Clinical Feature Extraction

**User Story:** As a User, I want the Platform to automatically extract relevant clinical features from uploaded documents, so that I do not have to manually re-enter data that is already in the records.

#### Acceptance Criteria

1. WHEN documents are successfully uploaded, THE Document_Parser SHALL extract all available Clinical_Features from the document content.
2. THE Feature_Extractor SHALL map extracted values to the standardized Clinical_Features schema, preserving original units and terminology.
3. WHEN a Clinical_Feature value cannot be found in any uploaded document, THE Feature_Extractor SHALL mark that feature as `missing` rather than assuming a default value.
4. THE Platform SHALL present the extracted Clinical_Features to the User for review and correction before classification is performed.
5. WHEN a User corrects or supplements an extracted feature value, THE Platform SHALL record the correction alongside the original extracted value in the Audit_Trail.
6. IF no Clinical_Features can be extracted from the uploaded documents, THEN THE Platform SHALL notify the User and request manual entry or additional documents before proceeding.

---

### Requirement 3: Manual Clinical Feature Entry

**User Story:** As a User, I want to manually enter clinical feature values, so that I can classify cases where structured documents are unavailable or incomplete.

#### Acceptance Criteria

1. THE Platform SHALL provide a structured data entry form covering all Clinical_Features.
2. WHEN a User submits the manual entry form, THE Platform SHALL validate that tumor size is a positive numeric value in millimeters, histological grade is one of I, II, or III, and all enumerated fields contain only permitted values.
3. IF a required field is submitted with an invalid value, THEN THE Platform SHALL highlight the invalid field and display the permitted value range or options.
4. THE Platform SHALL allow classification to proceed when at least tumor size, histological grade, and margin type are provided, treating all other missing features as `missing` in the Audit_Trail.

---

### Requirement 4: Severity Classification

**User Story:** As a User, I want the Platform to classify the tumor severity based on the extracted or entered clinical features, so that I can understand whether the tumor is benign or malignant and, if malignant, its stage.

#### Acceptance Criteria

1. WHEN all required Clinical_Features are available or marked `missing`, THE Severity_Engine SHALL execute a two-step classification pipeline: first running the Classifier to determine benign vs. malignant, then invoking the TNM_Rule_Engine to assign a stage (I–IV) only if the result is malignant.
2. THE Classifier SHALL use a validated ensemble model (e.g., combining gradient boosting and a calibrated neural network) trained on a clinically annotated dataset with a minimum reported AUC of 0.97 for benign/malignant discrimination on a held-out test set.
3. THE Severity_Engine SHALL use the TNM_Rule_Engine for all staging decisions; staging SHALL NOT be performed by ML inference alone.
4. WHEN the Classifier produces a `Benign` result, THE Severity_Engine SHALL NOT invoke the TNM_Rule_Engine and SHALL NOT assign a stage to the result.
5. THE Severity_Engine SHALL produce exactly one Severity_Label per classification request.
6. THE Classifier SHALL include a Calibration_Layer so that the Confidence_Score reflects true empirical probability; THE Platform SHALL generate reliability curves during validation to verify calibration quality.
7. THE Severity_Engine SHALL produce a Confidence_Score in the range [0.0, 1.0] alongside the Severity_Label.
8. WHEN the Confidence_Score is below 0.75, THE Platform SHALL display a low-confidence warning alongside the result, advising the User to seek additional clinical review.
9. THE Severity_Engine SHALL enforce Grounded_Output: strict grounding enforced through rule-based TNM validation, audit trail traceability, and no implicit inference.
10. WHEN a Clinical_Feature is marked `missing`, THE Severity_Engine SHALL reduce the Confidence_Score according to the feature's criticality tier: each missing Tier 1 feature (tumor size, lymph node involvement, histological grade) SHALL reduce the Confidence_Score by 0.15; each missing Tier 2 feature (ER status, HER2 status, margin type) SHALL reduce the Confidence_Score by 0.08; each missing Tier 3 feature (PR status, Ki-67, mitotic rate) SHALL reduce the Confidence_Score by 0.04.

---

### Requirement 5: Result Presentation and Audit Trail

**User Story:** As a User, I want to see a clear, explainable result with a full audit trail, so that I can trust the output and understand exactly what data drove the classification.

#### Acceptance Criteria

1. WHEN a classification is complete, THE Platform SHALL display the Severity_Label, Confidence_Score, and a feature-importance summary showing the top contributing Clinical_Features.
2. THE Platform SHALL display the Audit_Trail, linking each Clinical_Feature value used in classification to its source (document reference ID and page/section, or "manual entry", or "missing").
3. THE Platform SHALL render the result in a format suitable for inclusion in a clinical report (printable PDF export).
4. WHEN a User requests a PDF export, THE Platform SHALL generate and deliver the report within 10 seconds.
5. THE Platform SHALL display a mandatory disclaimer stating that the classification is a decision-support tool and does not replace professional medical diagnosis.

---

### Requirement 6: No-Hallucination Guarantee

**User Story:** As a User, I want to be certain that every value in the output is traceable to the input data, so that I can trust the Platform in a clinical context.

#### Acceptance Criteria

1. THE Severity_Engine SHALL only use feature values that are present in the submitted documents or entered by the User.
2. WHEN a feature value is absent, THE Severity_Engine SHALL treat it as `missing` and SHALL NOT substitute an assumed, average, or inferred value without explicit User confirmation.
3. THE Platform SHALL include in every result a completeness indicator showing the percentage of Clinical_Features that were present vs. missing.
4. IF the completeness indicator is below 60%, THEN THE Platform SHALL display a data-sufficiency warning before showing the Severity_Label, requiring the User to acknowledge the warning before proceeding.
5. THE Platform SHALL enforce Grounded_Output through rule-based TNM validation, audit trail traceability, and no implicit inference.

---

### Requirement 7: Model Accuracy and Validation

**User Story:** As an Admin, I want the Classifier to meet defined accuracy thresholds on validated datasets, so that the Platform can be trusted for clinical decision support.

#### Acceptance Criteria

1. THE Classifier SHALL achieve a sensitivity (recall for malignant cases) of at least 0.95 on the held-out test set.
2. THE Classifier SHALL achieve a specificity of at least 0.90 on the held-out test set.
3. THE Classifier SHALL achieve an overall accuracy of at least 0.93 on the held-out test set.
4. THE Classifier SHALL be validated on a held-out test set drawn from at least two public datasets (e.g., CBIS-DDSM for imaging features, TCGA-BRCA for molecular/pathology features) with no patient overlap between training and test sets.
5. THE Platform SHALL store model version, training dataset provenance, and evaluation metrics in a model registry accessible to the Admin.
6. WHEN a new model version is deployed, THE Platform SHALL run an automated regression test against a fixed validation set and SHALL NOT deploy the new version if any metric falls below the thresholds in criteria 1–3.
7. THE Platform SHALL log every classification request and result for post-deployment monitoring and periodic model re-evaluation.

---

### Requirement 8: Security and Data Privacy

**User Story:** As a User, I want patient data to be handled securely, so that the Platform complies with medical data privacy regulations.

#### Acceptance Criteria

1. THE Platform SHALL encrypt all uploaded documents and extracted Clinical_Features at rest using AES-256.
2. THE Platform SHALL transmit all data between the client and server over TLS 1.2 or higher.
3. WHEN a classification session ends, THE Platform SHALL provide the User with the option to permanently delete all uploaded documents and extracted data from the Platform's storage.
4. THE Platform SHALL enforce role-based access control, ensuring that only authenticated Users and Admins can initiate classification requests or access results.
5. IF an unauthenticated request is made to any classification or data endpoint, THEN THE Platform SHALL return an HTTP 401 response and SHALL NOT process the request.
6. THE Platform SHALL store encryption keys in a hardware security module (HSM) or cloud key management service (e.g., AWS KMS, HashiCorp Vault); encryption keys SHALL NOT be stored in environment variables or source code.

---

### Requirement 9: Document Parser Data Integrity

**User Story:** As a developer, I want the Document_Parser to reliably serialize and deserialize clinical feature data, so that no information is lost or corrupted between extraction and classification.

#### Acceptance Criteria

1. THE Platform SHALL use a schema-validated JSON representation for all extracted Clinical_Features, and SHALL raise a data-integrity error if deserialization produces a result that fails schema validation.

---

### Requirement 10: DICOM Imaging Pipeline

**User Story:** As a User, I want the Platform to automatically extract imaging-derived clinical features from DICOM files, so that radiological findings are incorporated into classification without manual re-entry.

#### Acceptance Criteria

1. WHEN a DICOM file is uploaded, THE Platform SHALL run the Imaging_Model to perform tumor segmentation and extract tumor shape, margin type, and density estimation.
2. THE Imaging_Model SHALL classify tumor shape as regular or irregular, margin type as one of circumscribed/spiculated/microlobulated/obscured/indistinct, and density as a numeric estimate.
3. WHEN the Imaging_Model produces a confidence value below 0.85 for any extracted imaging feature, THE Platform SHALL mark that feature as `missing` and prompt the User to confirm or correct the value before classification proceeds.
4. THE Platform SHALL record in the Audit_Trail whether each imaging-derived Clinical_Feature was accepted as extracted, corrected by the User, or marked `missing`.

---

### Requirement 11: Asynchronous Processing SLA

**User Story:** As a User, I want the Platform to handle large or imaging-heavy classification requests without blocking, so that I receive timely feedback regardless of request complexity.

#### Acceptance Criteria

1. WHEN a classification request includes total uploaded data exceeding 10 MB or requires CNN inference via the Imaging_Model, THE Platform SHALL return a task ID to the User immediately and SHALL complete classification within 60 seconds for 95% of such requests.
2. WHEN a classification request includes total uploaded data of 10 MB or less and does not require CNN inference, THE Platform SHALL return the classification result synchronously within 10 seconds.
3. THE Platform SHALL allow the User to poll or subscribe to the task ID to retrieve the result when asynchronous processing is complete.
4. IF an asynchronous classification task exceeds 60 seconds, THEN THE Platform SHALL notify the User of the delay and provide an updated estimated completion time.

---

### Requirement 12: Clinician Override Monitoring and Retraining Trigger

**User Story:** As an Admin, I want the Platform to monitor clinician overrides of classification results, so that systematic model errors can be detected and trigger retraining.

#### Acceptance Criteria

1. THE Platform SHALL log every instance where a User overrides the Severity_Label produced by the Severity_Engine, recording the original label, the override label, the timestamp, and the User identifier.
2. THE Platform SHALL compute the clinician override rate as a rolling 30-day percentage of classification requests that received an override.
3. IF the rolling 30-day override rate exceeds 10%, THEN THE Platform SHALL automatically send a model retraining pipeline notification to the Admin.
4. THE Platform SHALL make the override rate metric and override log accessible to the Admin through the model registry dashboard.

---

### Requirement 13: Deployment

**User Story:** As a developer or operator, I want to deploy the Platform using either a containerized Docker setup or a native local setup, so that I can run the full system in environments with or without Docker available.

#### Acceptance Criteria

1. THE Platform SHALL support a Docker-based deployment method in which a single `docker compose up` command starts all services — frontend, backend, ML model service, and database — without requiring any additional manual steps beyond providing a populated environment configuration file.
2. WHEN the Docker-based deployment is used, THE Platform SHALL use a `docker-compose.yml` file that defines each service, its build context or image, exposed ports, inter-service dependencies, and environment variable bindings.
3. WHEN the Docker-based deployment is used, THE Platform SHALL read all runtime configuration (database credentials, API keys, model paths, allowed origins) from a `.env` file located in the project root, and SHALL NOT hard-code any environment-specific values in the image or compose file.
4. THE Platform SHALL support a non-Docker (native) deployment method in which each service can be installed and started directly on the host machine using standard tooling: `pip` with a virtual environment for the backend and ML model service, and `npm` for the frontend.
5. WHEN the non-Docker deployment is used, THE Platform SHALL provide a dependency manifest for each service (`requirements.txt` for Python services, `package.json` for the frontend) that fully specifies all required packages and versions needed to run that service.
6. WHEN the non-Docker deployment is used, THE Platform SHALL accept the same environment variables as the Docker-based deployment, resolved from a `.env` file or from the host shell environment, so that configuration is consistent across both methods.
7. IF a required environment variable is absent at startup under either deployment method, THEN THE Platform SHALL log a descriptive error identifying the missing variable and SHALL NOT start the affected service.
8. THE Platform SHALL expose the same service ports and API surface under both deployment methods, so that a client configured for one method requires no changes to connect to the other.
