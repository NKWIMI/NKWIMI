import os
import cv2
import numpy as np
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class DocumentAIService:
    """AI service for document verification and fraud detection"""
    
    def __init__(self):
        self.model_path = os.path.join(settings.BASE_DIR, 'ml_models')
        self.models_loaded = False
        self.load_models()
    
    def load_models(self):
        """Load pre-trained AI models"""
        try:
            # Check if model files exist
            classification_model_path = os.path.join(self.model_path, 'document_classifier.h5')
            fraud_model_path = os.path.join(self.model_path, 'fraud_detector.pkl')
            vectorizer_path = os.path.join(self.model_path, 'tfidf_vectorizer.pkl')
            
            if (os.path.exists(classification_model_path) and 
                os.path.exists(fraud_model_path) and 
                os.path.exists(vectorizer_path)):
                
                # Import here to avoid dependencies if models don't exist
                import tensorflow as tf
                import joblib
                
                self.classification_model = tf.keras.models.load_model(classification_model_path)
                self.fraud_model = joblib.load(fraud_model_path)
                self.vectorizer = joblib.load(vectorizer_path)
                self.models_loaded = True
                logger.info("AI models loaded successfully")
            else:
                logger.warning("AI model files not found. Using fallback verification.")
                self.models_loaded = False
                
        except ImportError as e:
            logger.warning(f"AI dependencies not installed: {e}")
            self.models_loaded = False
        except Exception as e:
            logger.error(f"Error loading AI models: {e}")
            self.models_loaded = False
    
    def extract_text_from_image(self, image_path):
        """Extract text from document image using OCR"""
        try:
            # Try to import pytesseract
            try:
                import pytesseract
                from PIL import Image
            except ImportError:
                logger.warning("Pytesseract not installed. OCR disabled.")
                return ""
            
            text = pytesseract.image_to_string(Image.open(image_path))
            return text.strip()
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""
    
    def preprocess_image(self, image_path, target_size=(224, 224)):
        """Preprocess image for model input"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError("Could not read image")
            img = cv2.resize(img, target_size)
            img = img / 255.0  # Normalize
            img = np.expand_dims(img, axis=0)
            return img
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return None
    
    def verify_document_type_basic(self, document_file):
        """Basic document type verification without AI models"""
        # Simple file extension check as fallback
        valid_extensions = ['.jpg', '.jpeg', '.png', '.pdf']
        file_extension = os.path.splitext(document_file.name)[1].lower()
        
        if file_extension not in valid_extensions:
            return False, f"Invalid file format: {file_extension}"
        
        # Basic size check
        if document_file.size > 10 * 1024 * 1024:  # 10MB limit
            return False, "File too large"
        
        return True, "basic_validation"
    
    def verify_document_type(self, document_file):
        """Verify if document is a valid identity document"""
        if not self.models_loaded:
            return self.verify_document_type_basic(document_file)
        
        try:
            # Save temporary file for processing
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(document_file.name)[1]) as tmp:
                for chunk in document_file.chunks():
                    tmp.write(chunk)
                temp_path = tmp.name
            
            # Preprocess image
            processed_img = self.preprocess_image(temp_path)
            if processed_img is None:
                os.remove(temp_path)
                return False, "Image processing failed"
            
            # Predict document type
            prediction = self.classification_model.predict(processed_img)
            confidence = np.max(prediction)
            predicted_class = np.argmax(prediction)
            
            # Document types: 0=invalid, 1=ID card, 2=passport, 3=driver license
            document_types = ['invalid', 'id_card', 'passport', 'driver_license']
            
            is_valid = predicted_class != 0 and confidence > 0.7
            
            # Clean up
            os.remove(temp_path)
            
            return is_valid, document_types[predicted_class]
            
        except Exception as e:
            logger.error(f"Document verification failed: {e}")
            return self.verify_document_type_basic(document_file)
    
    def detect_fraud_patterns_basic(self, document_text, user_data):
        """Basic fraud detection without AI models"""
        warnings = []
        
        # Simple text length check
        if not document_text or len(document_text.strip()) < 10:
            warnings.append("Document text too short or unreadable")
        
        # Basic pattern checks
        if document_text and user_data.get('first_name'):
            if user_data['first_name'].lower() not in document_text.lower():
                warnings.append("Name not found in document")
        
        return len(warnings) > 0, warnings
    
    def detect_fraud_patterns(self, document_text, user_data):
        """Detect potential fraud patterns in document text"""
        if not self.models_loaded:
            return self.detect_fraud_patterns_basic(document_text, user_data)
        
        try:
            if not document_text:
                return False, ["No text extracted from document"]
            
            # Vectorize text
            text_vector = self.vectorizer.transform([document_text])
            
            # Prepare user data features
            user_features = self._extract_user_features(user_data)
            
            # Combine features for fraud detection
            combined_features = np.hstack([text_vector.toarray(), user_features])
            
            # Predict fraud probability
            fraud_probability = self.fraud_model.predict_proba(combined_features)[0][1]
            
            is_fraud = fraud_probability > 0.6
            
            return is_fraud, [f"Fraud probability: {fraud_probability:.2f}"] if is_fraud else []
            
        except Exception as e:
            logger.error(f"Fraud detection failed: {e}")
            return self.detect_fraud_patterns_basic(document_text, user_data)
    
    def _extract_user_features(self, user_data):
        """Extract relevant features from user data for fraud detection"""
        features = []
        
        # Example features
        features.append(1 if user_data.get('phone_number') else 0)
        features.append(1 if user_data.get('address') else 0)
        features.append(1 if user_data.get('email') else 0)
        
        # Age feature if available
        if user_data.get('date_of_birth'):
            age = (timezone.now().date() - user_data['date_of_birth']).days // 365
            features.append(age)
        else:
            features.append(0)
        
        return np.array(features).reshape(1, -1)
    
    def check_document_consistency(self, extracted_text, user_profile):
        """Check consistency between document text and user profile"""
        inconsistencies = []
        
        if not extracted_text:
            return ["No text extracted from document"]
        
        # Check name consistency
        if user_profile.first_name and user_profile.last_name:
            user_name = f"{user_profile.first_name} {user_profile.last_name}".lower()
            if user_name not in extracted_text.lower():
                inconsistencies.append("Name mismatch between document and profile")
        
        return inconsistencies
    
    def generate_risk_score(self, document_file, user_profile):
        """Generate comprehensive risk score for document verification"""
        risk_score = 0
        warnings = []
        
        # Verify document type
        is_valid, doc_type = self.verify_document_type(document_file)
        if not is_valid:
            risk_score += 40
            warnings.append(f"Document validation failed: {doc_type}")
        
        # Extract text for further analysis (save to temp file for OCR)
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(document_file.name)[1]) as tmp:
            for chunk in document_file.chunks():
                tmp.write(chunk)
            temp_path = tmp.name
        
        extracted_text = self.extract_text_from_image(temp_path)
        os.remove(temp_path)
        
        # Check consistency with user profile
        inconsistencies = self.check_document_consistency(extracted_text, user_profile)
        if inconsistencies:
            risk_score += len(inconsistencies) * 20
            warnings.extend(inconsistencies)
        
        # Detect fraud patterns
        user_data = {
            'first_name': user_profile.first_name,
            'last_name': user_profile.last_name,
            'email': user_profile.email,
            'phone_number': user_profile.phone_number,
            'address': user_profile.address_text,
            'date_of_birth': user_profile.date_of_birth
        }
        
        is_fraud, fraud_warnings = self.detect_fraud_patterns(extracted_text, user_data)
        if is_fraud:
            risk_score += 30
            warnings.extend(fraud_warnings)
        
        return min(risk_score, 100), warnings