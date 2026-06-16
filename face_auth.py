import os
import cv2
import numpy as np

class USBFaceAuth:
    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        self.model_path = os.path.join(self.model_dir, "face_model.xml")
        
        # Load Haar Cascade face detector
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if not os.path.exists(cascade_path):
            raise FileNotFoundError("Haar Cascade XML not found in OpenCV package.")
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Initialize recognizer
        self.recognizer = self._init_recognizer()
        self.is_trained = os.path.exists(self.model_path)
        if self.is_trained:
            try:
                self.recognizer.read(self.model_path)
            except Exception as e:
                print(f"Failed to load existing face model: {e}")
                self.is_trained = False

    def _init_recognizer(self):
        """Initializes the LBPH face recognizer with fallback support."""
        try:
            return cv2.face.LBPHFaceRecognizer_create()
        except AttributeError:
            try:
                # Older or alternative binding paths
                return cv2.face_LBPHFaceRecognizer.create()
            except AttributeError:
                raise ImportError(
                    "OpenCV face recognition module (LBPH) is not available.\n"
                    "Make sure you have installed 'opencv-contrib-python' instead of 'opencv-python'."
                )

    def detect_face(self, frame):
        """
        Detects a face in the frame.
        Returns (gray_face_image, bounding_box) or (None, None) if no face detected.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Equalize histogram to improve contrast/lighting differences
        gray = cv2.equalizeHist(gray)
        
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.2, 
            minNeighbors=5, 
            minSize=(100, 100)
        )
        
        if len(faces) == 0:
            return None, None
            
        # Select the largest face (most likely the user closest to camera)
        largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
        x, y, w, h = largest_face
        
        # Crop and resize to uniform size
        face_roi = gray[y:y+h, x:x+w]
        face_resized = cv2.resize(face_roi, (200, 200))
        
        return face_resized, (x, y, w, h)

    def train_model(self, face_samples, label=1) -> bool:
        """
        Trains the LBPH recognizer on the provided list of grayscale face images.
        All samples are trained with a single label (1, indicating the registered owner).
        Saves the model to model_path.
        """
        if len(face_samples) < 10:
            print("Insufficient face samples to train. Need at least 10.")
            return False
            
        labels = np.array([label] * len(face_samples), dtype=np.int32)
        
        try:
            self.recognizer.train(face_samples, labels)
            self.recognizer.write(self.model_path)
            self.is_trained = True
            return True
        except Exception as e:
            print(f"Error training face recognizer: {e}")
            return False

    def verify_face(self, face_img) -> tuple[bool, float]:
        """
        Matches a face image against the trained model.
        Returns (is_match, distance_score).
        For LBPH, the output is a distance score where:
        - 0 is a perfect match.
        - < 55 is a very strong match.
        - < 70 is an acceptable match.
        - > 75 is a mismatch.
        """
        if not self.is_trained:
            return False, 999.0
            
        try:
            label, distance = self.recognizer.predict(face_img)
            # Distance threshold of 65.0 is standard for LBPH under varied lighting
            is_match = (label == 1) and (distance < 65.0)
            return is_match, distance
        except Exception as e:
            print(f"Error predicting face: {e}")
            return False, 999.0

    def clear_model(self):
        """Removes the trained face model file."""
        if os.path.exists(self.model_path):
            try:
                os.remove(self.model_path)
            except Exception:
                pass
        self.is_trained = False
        self.recognizer = self._init_recognizer()
