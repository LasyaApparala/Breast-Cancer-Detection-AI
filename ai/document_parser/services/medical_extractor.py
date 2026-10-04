import re
import json
from typing import Dict, List, Any, Optional, Tuple
import pdfplumber
import pytesseract
from PIL import Image
import pydicom
from docx import Document
import pandas as pd
import spacy
from transformers import AutoTokenizer, AutoModel
import numpy as np
from datetime import datetime
import hashlib

class MedicalDocumentExtractor:
    """Advanced medical document parser for breast cancer reports and imaging"""
    
    def __init__(self):
        # Load medical NLP model
        try:
            self.nlp = spacy.load("en_core_medical_trf")
        except OSError:
            # Fallback to base model if medical model not available
            self.nlp = spacy.load("en_core_web_trf")
        
        # Load BioBERT for medical text understanding
        try:
            self.tokenizer = AutoTokenizer.from_pretrained("dmis-lab/biobert-base-cased-v1.1")
            self.text_model = AutoModel.from_pretrained("dmis-lab/biobert-base-cased-v1.1")
        except Exception:
            self.tokenizer = None
            self.text_model = None
    
    async def extract_clinical_data(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Extract structured clinical data from medical documents
        
        Args:
            file_path: Path to the medical document
            file_type: Type of document (pdf, dicom, docx, etc.)
            
        Returns:
            Dictionary with extracted clinical features
        """
        
        try:
            if file_type == 'pdf':
                return await self._extract_from_pdf(file_path)
            elif file_type == 'dicom':
                return await self._extract_from_dicom(file_path)
            elif file_type == 'docx':
                return await self._extract_from_docx(file_path)
            elif file_type in ['jpg', 'jpeg', 'png', 'tiff']:
                return await self._extract_from_image(file_path)
            else:
                return {"error": f"Unsupported file type: {file_type}"}
                
        except Exception as e:
            return {"error": f"Failed to extract from {file_type}: {str(e)}"}
    
    async def _extract_from_pdf(self, file_path: str) -> Dict[str, Any]:
        """Extract clinical data from PDF pathology/radiology reports"""
        extracted_data = {}
        
        with pdfplumber.open(file_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
        
        # Extract structured information using NLP and regex
        extracted_data.update(self._extract_pathology_findings(full_text))
        extracted_data.update(self._extract_tumor_details(full_text))
        extracted_data.update(self._extract_receptor_status(full_text))
        extracted_data.update(self._extract_staging_info(full_text))
        extracted_data.update(self._extract_bi_rads_score(full_text))
        
        # Add metadata
        extracted_data["extraction_metadata"] = {
            "file_type": "pdf",
            "pages": len(pdf.pages),
            "text_length": len(full_text),
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "confidence_score": self._calculate_extraction_confidence(extracted_data)
        }
        
        return extracted_data
    
    async def _extract_from_dicom(self, file_path: str) -> Dict[str, Any]:
        """Extract clinical data from DICOM imaging files"""
        extracted_data = {}
        
        try:
            ds = pydicom.dcmread(file_path)
            
            # Extract imaging metadata
            extracted_data["imaging_metadata"] = {
                "modality": getattr(ds, 'Modality', 'Unknown'),
                "study_date": str(getattr(ds, 'StudyDate', '')),
                "patient_id": str(getattr(ds, 'PatientID', '')),
                "study_description": str(getattr(ds, 'StudyDescription', '')),
                "image_size": f"{getattr(ds, 'Rows', 0)}x{getattr(ds, 'Columns', 0)}",
                "slice_thickness": str(getattr(ds, 'SliceThickness', 'Unknown')),
                " kvp": str(getattr(ds, 'KVP', 'Unknown'))
            }
            
            # Extract radiology report if present
            if hasattr(ds, 'RadiologyReport'):
                report_text = str(ds.RadiologyReport)
                extracted_data.update(self._extract_pathology_findings(report_text))
                extracted_data.update(self._extract_tumor_details(report_text))
            
            # Perform OCR on image if no text report
            if hasattr(ds, 'pixel_array'):
                pixel_array = ds.pixel_array
                image = Image.fromarray(pixel_array)
                text = pytesseract.image_to_string(image)
                if text.strip():
                    extracted_data.update(self._extract_pathology_findings(text))
            
        except Exception as e:
            extracted_data["error"] = f"DICOM processing error: {str(e)}"
        
        extracted_data["extraction_metadata"] = {
            "file_type": "dicom",
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "confidence_score": extracted_data.get("confidence_score", 0.5)
        }
        
        return extracted_data
    
    async def _extract_from_docx(self, file_path: str) -> Dict[str, Any]:
        """Extract clinical data from Word documents"""
        extracted_data = {}
        
        doc = Document(file_path)
        full_text = ""
        
        for paragraph in doc.paragraphs:
            full_text += paragraph.text + "\n"
        
        # Extract structured information
        extracted_data.update(self._extract_pathology_findings(full_text))
        extracted_data.update(self._extract_tumor_details(full_text))
        extracted_data.update(self._extract_receptor_status(full_text))
        extracted_data.update(self._extract_staging_info(full_text))
        
        extracted_data["extraction_metadata"] = {
            "file_type": "docx",
            "paragraphs": len(doc.paragraphs),
            "text_length": len(full_text),
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "confidence_score": self._calculate_extraction_confidence(extracted_data)
        }
        
        return extracted_data
    
    async def _extract_from_image(self, file_path: str) -> Dict[str, Any]:
        """Extract text from medical images using OCR"""
        extracted_data = {}
        
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            
            if text.strip():
                extracted_data.update(self._extract_pathology_findings(text))
                extracted_data.update(self._extract_tumor_details(text))
                extracted_data.update(self._extract_receptor_status(text))
            
            extracted_data["extraction_metadata"] = {
                "file_type": "image",
                "image_size": f"{image.width}x{image.height}",
                "text_length": len(text),
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "confidence_score": self._calculate_extraction_confidence(extracted_data)
            }
            
        except Exception as e:
            extracted_data["error"] = f"Image OCR error: {str(e)}"
        
        return extracted_data
    
    def _extract_pathology_findings(self, text: str) -> Dict[str, Any]:
        """Extract pathology findings using medical NLP"""
        findings = {}
        
        # Use spaCy for medical entity recognition
        doc = self.nlp(text)
        
        # Extract tumor characteristics
        tumor_patterns = {
            r'tumor\s+size[:\s]*([0-9.]+)\s*cm': 'tumor_size_cm',
            r'(\d+(?:\.\d+)?)\s*cm\s+tumor': 'tumor_size_cm',
            r'grade\s*([1-3])': 'tumor_grade',
            r'histologic\s+grade\s*([1-3])': 'tumor_grade',
            r'well\s+differentiated': 'grade_well_differentiated',
            r'moderately\s+differentiated': 'grade_moderately_differentiated',
            r'poorly\s+differentiated': 'grade_poorly_differentiated'
        }
        
        for pattern, key in tumor_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if 'size' in key:
                    findings[key] = float(match.group(1))
                elif 'grade' in key:
                    findings[key] = int(match.group(1))
                else:
                    findings[key] = True
        
        # Extract lymph node status
        lymph_patterns = {
            r'lymph\s+node[s]?.*positive': 'lymph_nodes_positive',
            r'lymph\s+node[s]?.*negative': 'lymph_nodes_negative',
            r'(\d+)\s+lymph\s+node[s]?.*positive': 'positive_lymph_nodes_count',
            r'lymph\s+node[s]?.*metastasis': 'lymph_node_metastasis'
        }
        
        for pattern, key in lymph_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if 'count' in key:
                    findings[key] = int(match.group(1))
                else:
                    findings[key] = True
        
        # Extract metastasis information
        metastasis_patterns = {
            r'distant\s+metastasis': 'distant_metastasis',
            r'metastatic\s+disease': 'distant_metastasis',
            r'no\s+evidence\s+of\s+metastasis': 'no_distant_metastasis',
            r'mets\s+to\s+(\w+)': 'metastasis_location'
        }
        
        for pattern, key in metastasis_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if 'location' in key:
                    findings[key] = match.group(1)
                else:
                    findings[key] = True
        
        return findings
    
    def _extract_tumor_details(self, text: str) -> Dict[str, Any]:
        """Extract specific tumor details"""
        details = {}
        
        # Tumor size patterns
        size_patterns = [
            r'(\d+(?:\.\d+)?)\s*cm',
            r'(\d+(?:\.\d+)?)\s*millimeter',
            r'(\d+(?:\.\d+)?)\s*mm'
        ]
        
        for pattern in size_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                sizes = [float(m) for m in matches]
                if 'mm' in pattern:
                    sizes = [s/10 for s in sizes]  # Convert mm to cm
                details['tumor_sizes_found'] = sizes
                details['max_tumor_size'] = max(sizes)
                break
        
        # Tumor type
        tumor_types = {
            r'ductal\s+carcinoma': 'ductal_carcinoma',
            r'lobular\s+carcinoma': 'lobular_carcinoma',
            r'invasive\s+ductal\s+carcinoma': 'idc',
            r'invasive\s+lobular\s+carcinoma': 'ilc',
            r'ductal\s+carcinoma\s+in\s+situ': 'dcis'
        }
        
        for pattern, key in tumor_types.items():
            if re.search(pattern, text, re.IGNORECASE):
                details[key] = True
        
        return details
    
    def _extract_receptor_status(self, text: str) -> Dict[str, Any]:
        """Extract hormone receptor status"""
        receptors = {}
        
        # ER status
        er_patterns = {
            r'estrogen\s+receptor.*positive': 'er_positive',
            r'estrogen\s+receptor.*negative': 'er_negative',
            r'er\s*positive': 'er_positive',
            r'er\s*negative': 'er_negative',
            r'er\s*\+': 'er_positive',
            r'er\s*\-': 'er_negative'
        }
        
        # PR status
        pr_patterns = {
            r'progesterone\s+receptor.*positive': 'pr_positive',
            r'progesterone\s+receptor.*negative': 'pr_negative',
            r'pr\s*positive': 'pr_positive',
            r'pr\s*negative': 'pr_negative',
            r'pr\s*\+': 'pr_positive',
            r'pr\s*\-': 'pr_negative'
        }
        
        # HER2 status
        her2_patterns = {
            r'her2.*positive': 'her2_positive',
            r'her2.*negative': 'her2_negative',
            r'her2\s*\+': 'her2_positive',
            r'her2\s*\-': 'her2_negative',
            r'her2\s*amplified': 'her2_amplified'
        }
        
        # Ki-67 index
        ki67_patterns = [
            r'ki[-\s]*67[:\s]*(\d+(?:\.\d+)?)',
            r'mib[-\s]*1[:\s]*(\d+(?:\.\d+)?)',
            r'proliferative\s+index[:\s]*(\d+(?:\.\d+)?)'
        ]
        
        # Extract patterns
        for pattern, key in er_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                receptors['er_status'] = 'positive'
                break
        else:
            receptors['er_status'] = 'unknown'
        
        for pattern, key in pr_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                receptors['pr_status'] = 'positive'
                break
        else:
            receptors['pr_status'] = 'unknown'
        
        for pattern, key in her2_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                receptors['her2_status'] = 'positive'
                break
        else:
            receptors['her2_status'] = 'unknown'
        
        for pattern in ki67_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                receptors['ki67_index'] = float(match.group(1))
                break
        
        return receptors
    
    def _extract_staging_info(self, text: str) -> Dict[str, Any]:
        """Extract TNM staging information"""
        staging = {}
        
        # Tumor size (T)
        t_patterns = [
            r'([Tt])([0-4])',
            r'tumor\s*size.*([0-4])',
            r'([Tt])([1-4])[a-b]?'
        ]
        
        # Node involvement (N)
        n_patterns = [
            r'([Nn])([0-3])',
            r'node[s]?.*([0-3])',
            r'([Nn])([1-3])[a-b]?'
        ]
        
        # Metastasis (M)
        m_patterns = [
            r'([Mm])([0-1])',
            r'metastasis.*([0-1])',
            r'([Mm])([01])'
        ]
        
        for pattern in t_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                staging['t_stage'] = match.group(2)
                break
        
        for pattern in n_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                staging['n_stage'] = match.group(2)
                break
        
        for pattern in m_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                staging['m_stage'] = match.group(2)
                break
        
        # Extract overall stage
        stage_patterns = [
            r'stage\s*([0-4])',
            r'stage\s*([IVX]+)',
            r'([0-4])?[A-Z]?\s*stage'
        ]
        
        for pattern in stage_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                stage_text = match.group(1)
                # Convert Roman numerals to Arabic
                if stage_text.upper() in ['I', 'II', 'III', 'IV']:
                    roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}
                    staging['overall_stage'] = roman_map[stage_text.upper()]
                else:
                    staging['overall_stage'] = int(stage_text)
                break
        
        return staging
    
    def _extract_bi_rads_score(self, text: str) -> Dict[str, Any]:
        """Extract BI-RADS assessment score"""
        bi_rads = {}
        
        patterns = [
            r'bi[-\s]*rads\s*([1-6])',
            r'breast\s+imaging[-\s]*reporting\s+and\s+data\s+system\s*([1-6])',
            r'assessment\s*category\s*([1-6])',
            r'birads\s*([1-6])'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                bi_rads['bi_rads_score'] = int(match.group(1))
                break
        
        return bi_rads
    
    def _calculate_extraction_confidence(self, extracted_data: Dict[str, Any]) -> float:
        """Calculate confidence score for extraction quality"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on extracted fields
        if 'tumor_grade' in extracted_data:
            confidence += 0.1
        if 'er_status' in extracted_data and extracted_data['er_status'] != 'unknown':
            confidence += 0.1
        if 'pr_status' in extracted_data and extracted_data['pr_status'] != 'unknown':
            confidence += 0.1
        if 'her2_status' in extracted_data and extracted_data['her2_status'] != 'unknown':
            confidence += 0.1
        if 'ki67_index' in extracted_data:
            confidence += 0.05
        if 'bi_rads_score' in extracted_data:
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def generate_extraction_hash(self, file_content: bytes) -> str:
        """Generate hash for file content integrity verification"""
        return hashlib.sha256(file_content).hexdigest()[:16]
    
    def validate_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean extracted clinical data"""
        validated = {}
        
        # Validate tumor grade
        if 'tumor_grade' in data:
            grade = data['tumor_grade']
            if isinstance(grade, int) and 1 <= grade <= 3:
                validated['tumor_grade'] = grade
        
        # Validate receptor statuses
        for receptor in ['er_status', 'pr_status', 'her2_status']:
            if receptor in data and data[receptor] in ['positive', 'negative']:
                validated[receptor] = data[receptor]
        
        # Validate Ki-67
        if 'ki67_index' in data:
            ki67 = data['ki67_index']
            if isinstance(ki67, (int, float)) and 0 <= ki67 <= 100:
                validated['ki67_index'] = ki67
        
        # Validate BI-RADS
        if 'bi_rads_score' in data:
            score = data['bi_rads_score']
            if isinstance(score, int) and 1 <= score <= 6:
                validated['bi_rads_score'] = score
        
        # Copy metadata
        if 'extraction_metadata' in data:
            validated['extraction_metadata'] = data['extraction_metadata']
        
        return validated
