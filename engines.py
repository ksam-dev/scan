"""
Moteurs OCR/HTR pour ORIS
Ce module contient les implémentations des différents moteurs OCR et HTR
"""

import time
import cv2
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class OCREngine(ABC):
    """Classe abstraite pour les moteurs OCR/HTR"""
    
    @abstractmethod
    def process_image(self, image_path: str) -> Dict:
        """
        Traite une image et retourne les résultats OCR
        
        Args:
            image_path: Chemin vers l'image à traiter
            
        Returns:
            Dict contenant:
            - text: Texte extrait
            - confidence: Score de confiance
            - bounding_boxes: Coordonnées des zones de texte
            - processing_time: Temps de traitement
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie si le moteur est disponible"""
        pass


class TesseractEngine(OCREngine):
    """Moteur OCR Tesseract"""
    
    def __init__(self, config: str = '--oem 3 --psm 6'):
        self.config = config
        try:
            import pytesseract
            self.pytesseract = pytesseract
            self._available = True
        except ImportError:
            logger.error("pytesseract n'est pas installé")
            self._available = False
    
    def is_available(self) -> bool:
        return self._available
    
    def process_image(self, image_path: str) -> Dict:
        if not self.is_available():
            raise RuntimeError("Tesseract n'est pas disponible")
        
        start_time = time.time()
        
        try:
            # Lecture de l'image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Impossible de lire l'image: {image_path}")
            
            # Extraction du texte
            text = self.pytesseract.image_to_string(image, config=self.config)
            
            # Extraction des données détaillées
            data = self.pytesseract.image_to_data(image, config=self.config, output_type=self.pytesseract.Output.DICT)
            
            # Calcul de la confiance moyenne
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Extraction des bounding boxes
            bounding_boxes = []
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 0:
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    bounding_boxes.append({
                        'text': data['text'][i],
                        'confidence': int(data['conf'][i]),
                        'bbox': [x, y, x + w, y + h]
                    })
            
            processing_time = time.time() - start_time
            
            return {
                'text': text.strip(),
                'confidence': avg_confidence / 100.0,  # Normalisation 0-1
                'bounding_boxes': bounding_boxes,
                'processing_time': processing_time
            }
            
        except Exception as e:
            logger.error(f"Erreur Tesseract: {e}")
            return {
                'text': '',
                'confidence': 0.0,
                'bounding_boxes': [],
                'processing_time': time.time() - start_time,
                'error': str(e)
            }


class EasyOCREngine(OCREngine):
    """Moteur OCR EasyOCR"""
    
    def __init__(self, languages: List[str] = ['en', 'fr']):
        self.languages = languages
        try:
            import easyocr
            self.reader = easyocr.Reader(languages)
            self._available = True
        except ImportError:
            logger.error("easyocr n'est pas installé")
            self._available = False
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation d'EasyOCR: {e}")
            self._available = False
    
    def is_available(self) -> bool:
        return self._available
    
    def process_image(self, image_path: str) -> Dict:
        if not self.is_available():
            raise RuntimeError("EasyOCR n'est pas disponible")
        
        start_time = time.time()
        
        try:
            # Traitement de l'image
            results = self.reader.readtext(image_path)
            
            # Extraction du texte et des bounding boxes
            text_parts = []
            bounding_boxes = []
            confidences = []
            
            for (bbox, text, confidence) in results:
                text_parts.append(text)
                confidences.append(confidence)
                
                # Conversion des coordonnées
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                
                bounding_boxes.append({
                    'text': text,
                    'confidence': confidence,
                    'bbox': [x_min, y_min, x_max, y_max]
                })
            
            full_text = ' '.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            processing_time = time.time() - start_time
            
            return {
                'text': full_text,
                'confidence': avg_confidence,
                'bounding_boxes': bounding_boxes,
                'processing_time': processing_time
            }
            
        except Exception as e:
            logger.error(f"Erreur EasyOCR: {e}")
            return {
                'text': '',
                'confidence': 0.0,
                'bounding_boxes': [],
                'processing_time': time.time() - start_time,
                'error': str(e)
            }


class TrOCREngine(OCREngine):
    """Moteur HTR TrOCR pour l'écriture manuscrite"""
    
    def __init__(self, model_name: str = 'microsoft/trocr-base-handwritten'):
        self.model_name = model_name
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            from PIL import Image
            
            self.processor = TrOCRProcessor.from_pretrained(model_name)
            self.model = VisionEncoderDecoderModel.from_pretrained(model_name)
            self.Image = Image
            self._available = True
        except ImportError:
            logger.error("transformers ou PIL n'est pas installé")
            self._available = False
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de TrOCR: {e}")
            self._available = False
    
    def is_available(self) -> bool:
        return self._available
    
    def process_image(self, image_path: str) -> Dict:
        if not self.is_available():
            raise RuntimeError("TrOCR n'est pas disponible")
        
        start_time = time.time()
        
        try:
            # Chargement de l'image
            image = self.Image.open(image_path).convert('RGB')
            
            # Préparation des inputs
            pixel_values = self.processor(images=image, return_tensors="pt").pixel_values
            
            # Génération du texte
            generated_ids = self.model.generate(pixel_values)
            generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            processing_time = time.time() - start_time
            
            # TrOCR ne fournit pas de score de confiance direct
            # On utilise une estimation basée sur la longueur du texte généré
            confidence = min(0.9, len(generated_text) / 100.0) if generated_text else 0.0
            
            return {
                'text': generated_text,
                'confidence': confidence,
                'bounding_boxes': [],  # TrOCR ne fournit pas de bounding boxes
                'processing_time': processing_time
            }
            
        except Exception as e:
            logger.error(f"Erreur TrOCR: {e}")
            return {
                'text': '',
                'confidence': 0.0,
                'bounding_boxes': [],
                'processing_time': time.time() - start_time,
                'error': str(e)
            }


class OCREngineManager:
    """Gestionnaire des moteurs OCR/HTR"""
    
    def __init__(self):
        self.engines = {}
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialise tous les moteurs disponibles"""
        # Tesseract
        tesseract = TesseractEngine()
        if tesseract.is_available():
            self.engines['tesseract'] = tesseract
            logger.info("Tesseract initialisé avec succès")
        
        # EasyOCR
        easyocr = EasyOCREngine()
        if easyocr.is_available():
            self.engines['easyocr'] = easyocr
            logger.info("EasyOCR initialisé avec succès")
        
        # TrOCR
        trocr = TrOCREngine()
        if trocr.is_available():
            self.engines['trocr'] = trocr
            logger.info("TrOCR initialisé avec succès")
        
        logger.info(f"Moteurs OCR/HTR disponibles: {list(self.engines.keys())}")
    
    def get_engine(self, engine_name: str) -> Optional[OCREngine]:
        """Récupère un moteur par son nom"""
        return self.engines.get(engine_name)
    
    def get_available_engines(self) -> List[str]:
        """Retourne la liste des moteurs disponibles"""
        return list(self.engines.keys())
    
    def process_with_engine(self, engine_name: str, image_path: str) -> Dict:
        """Traite une image avec un moteur spécifique"""
        engine = self.get_engine(engine_name)
        if not engine:
            raise ValueError(f"Moteur '{engine_name}' non disponible")
        
        return engine.process_image(image_path)
    
    def detect_handwriting(self, image_path: str) -> bool:
        """
        Détecte si une image contient de l'écriture manuscrite
        
        Cette fonction utilise des heuristiques simples pour détecter l'écriture manuscrite.
        Dans une implémentation plus avancée, on pourrait utiliser un modèle de classification.
        """
        try:
            # Chargement de l'image
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                return False
            
            # Calcul de la variance de Laplacian (mesure de netteté)
            laplacian_var = cv2.Laplacian(image, cv2.CV_64F).var()
            
            # Détection des contours
            edges = cv2.Canny(image, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Heuristiques pour détecter l'écriture manuscrite:
            # - Variance de Laplacian plus faible (moins net)
            # - Plus de contours irréguliers
            # - Ratio hauteur/largeur des contours plus variable
            
            if len(contours) == 0:
                return False
            
            # Calcul des ratios aspect des contours
            aspect_ratios = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > 10 and h > 10:  # Filtrer les petits contours
                    aspect_ratios.append(h / w)
            
            if not aspect_ratios:
                return False
            
            # Variance des ratios d'aspect (plus élevée pour l'écriture manuscrite)
            aspect_variance = np.var(aspect_ratios)
            
            # Seuils empiriques (à ajuster selon les données)
            is_handwritten = (laplacian_var < 100 and aspect_variance > 0.5) or aspect_variance > 1.0
            
            return is_handwritten
            
        except Exception as e:
            logger.error(f"Erreur lors de la détection d'écriture manuscrite: {e}")
            return False
    
    def choose_best_engine(self, image_path: str, is_handwritten: Optional[bool] = None) -> str:
        """
        Choisit le meilleur moteur pour une image donnée
        
        Args:
            image_path: Chemin vers l'image
            is_handwritten: Si None, détection automatique
            
        Returns:
            Nom du moteur recommandé
        """
        if is_handwritten is None:
            is_handwritten = self.detect_handwriting(image_path)
        
        if is_handwritten:
            # Pour l'écriture manuscrite, privilégier TrOCR
            if 'trocr' in self.engines:
                return 'trocr'
            elif 'easyocr' in self.engines:
                return 'easyocr'
        else:
            # Pour l'imprimé, privilégier EasyOCR puis Tesseract
            if 'easyocr' in self.engines:
                return 'easyocr'
            elif 'tesseract' in self.engines:
                return 'tesseract'
        
        # Fallback sur le premier moteur disponible
        available = self.get_available_engines()
        return available[0] if available else None


# Instance globale du gestionnaire
ocr_manager = OCREngineManager()

