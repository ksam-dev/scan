# oris/ocr_logic.py
# cerely workers =celery -A scan worker --loglevel=info --pool=solo
# oris/ocr_logic.py

import logging
import os
import time
from typing import Dict

import cv2
import numpy as np
import pytesseract
from PIL import Image

import logging
import os
import time
import random # Importer random pour la simulation

logger = logging.getLogger(__name__)

# --- Initialisation des Moteurs (Singleton Pattern) ---
EASYOCR_READER = None
HTR_PROCESSOR = None
HTR_MODEL = None
TRANSFORMERS_AVAILABLE = False

def initialize_models():
    """
    Fonction pour charger les modèles d'IA à la demande.
    Cette fonction ne sera appelée que par le worker Celery.
    """
    global EASYOCR_READER, HTR_PROCESSOR, HTR_MODEL, TRANSFORMERS_AVAILABLE

    # Initialiser EasyOCR
    if EASYOCR_READER is None:
        try:
            import easyocr
            EASYOCR_READER = easyocr.Reader(['fr', 'en'], gpu=False)
            logger.info("Moteur EasyOCR initialisé avec succès.")
        except Exception as e:
            logger.error(f"Impossible d'initialiser EasyOCR : {e}")

    # Initialiser TrOCR (HTR)
    if HTR_MODEL is None and not TRANSFORMERS_AVAILABLE:
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            HTR_PROCESSOR = TrOCRProcessor.from_pretrained('microsoft/trocr-base-handwritten')
            HTR_MODEL = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-base-handwritten')
            TRANSFORMERS_AVAILABLE = True
            logger.info("Moteur TrOCR (HTR) initialisé avec succès.")
        except Exception as e:
            logger.error(f"Impossible d'initialiser TrOCR (HTR) : {e}")


def _preprocess_image_for_ocr(image_path: str, max_size: int = 1600) -> Image.Image:
    """
    Ouvre, nettoie et redimensionne une image pour l'OCR afin d'optimiser la mémoire.
    """
    img = Image.open(image_path).convert("RGB")
    
    # Redimensionner si l'image est trop grande
    if img.width > max_size or img.height > max_size:
        logger.info(f"Redimensionnement de l'image de {img.size} à une taille max de {max_size}px.")
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
    return img


class OCRProcessor:
    """Processeur OCR/HTR intelligent et performant pour ORIS."""

    def __init__(self):
        # S'assurer que les modèles sont initialisés
        initialize_models()

    def _detect_handwriting(self, image: Image.Image) -> bool:
        """Détecte l'écriture manuscrite à partir d'un objet Image PIL."""
        try:
            img_cv = np.array(image.convert('L')) # Convertir en niveaux de gris
            laplacian_var = cv2.Laplacian(img_cv, cv2.CV_64F).var()
            logger.info(f"Détection d'écriture - Variance Laplacien: {laplacian_var:.2f}")
            return laplacian_var > 400
        except Exception as e:
            logger.warning(f"Erreur lors de la détection d'écriture manuscrite : {e}")
            return False

    def _process_with_tesseract(self, image: Image.Image) -> Dict:
        try:
            text = pytesseract.image_to_string(image, lang='fra+eng', config='--psm 3')
            return {'text': text.strip(), 'confidence': 0.85 if text.strip() else 0.0}
        except Exception as e:
            logger.warning(f"Erreur Tesseract: {e}")
            return {'text': '', 'confidence': 0.0}

    def _process_with_easyocr(self, image: Image.Image) -> Dict:
        if not EASYOCR_READER: return {'text': '', 'confidence': 0.0}
        try:
            img_np = np.array(image)
            results = EASYOCR_READER.readtext(img_np)
            if not results: return {'text': '', 'confidence': 0.0}
            text_parts = [res[1] for res in results]
            confidences = [res[2] for res in results]
            return {'text': ' '.join(text_parts), 'confidence': sum(confidences) / len(confidences)}
        except Exception as e:
            logger.warning(f"Erreur EasyOCR: {e}")
            return {'text': '', 'confidence': 0.0}

    def _process_with_htr(self, image: Image.Image) -> Dict:
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("TrOCR non disponible, utilisation de EasyOCR comme alternative.")
            return self._process_with_easyocr(image)
        try:
            pixel_values = HTR_PROCESSOR(images=image, return_tensors="pt").pixel_values
            generated_ids = HTR_MODEL.generate(pixel_values)
            text = HTR_PROCESSOR.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return {'text': text.strip(), 'confidence': 0.90 if text.strip() else 0.0}
        except Exception as e:
            logger.warning(f"Erreur TrOCR (HTR): {e}")
            return {'text': '', 'confidence': 0.0}

    def _merge_results(self, results: Dict) -> Dict:
        if not results: return {'text': '', 'confidence': 0.0, 'engine': 'none'}
        best_engine = max(results, key=lambda engine: len(results[engine]['text']))
        best_result = results[best_engine]
        best_result['engine'] = best_engine
        return best_result

    def process_image(self, image_path: str) -> Dict:
        start_time = time.time()
        logger.info(f"Début du traitement OCR pour : {os.path.basename(image_path)}")

        try:
            preprocessed_image = _preprocess_image_for_ocr(image_path)
            is_handwritten = self._detect_handwriting(preprocessed_image)

            if is_handwritten:
                logger.info("Type de contenu détecté : ÉCRITURE MANUSCRITE. Utilisation du moteur HTR.")
                result = self._process_with_htr(preprocessed_image)
                result['engine'] = 'trocr_handwritten'
            else:
                logger.info("Type de contenu détecté : TEXTE IMPRIMÉ. Utilisation d'une stratégie multi-moteurs.")
                tesseract_res = self._process_with_tesseract(preprocessed_image)
                easyocr_res = self._process_with_easyocr(preprocessed_image)
                result = self._merge_results({'tesseract': tesseract_res, 'easyocr': easyocr_res})

            result['processing_time'] = time.time() - start_time
            logger.info(f"Traitement terminé en {result['processing_time']:.2f}s. Moteur choisi: {result.get('engine', 'N/A')}, Confiance: {result.get('confidence', 0):.2%}")
            return result

        except Exception as e:
            logger.error(f"Erreur fatale lors du traitement OCR de {image_path}: {e}", exc_info=True)
            return {'text': '', 'confidence': 0.0, 'engine': 'error', 'processing_time': time.time() - start_time, 'error': str(e)}

    # --- NOUVELLE CLASSE DE MAQUETTE ---

class MockOCRProcessor:
    """
    Un "faux" processeur OCR pour le développement sur des machines à faibles ressources.
    Il ne charge aucun modèle et renvoie des résultats simulés instantanément.
    """
    def __init__(self):
        logger.info("Initialisation du PROCESSEUR OCR MAQUETTE (MockOCRProcessor).")
        self.mock_texts = [
            "Ceci est un texte de facture simulé. Montant total : 123.45 EUR.",
            "Contrat de service entre l'entreprise A et l'entreprise B. Date : 01/09/2025.",
            "Rapport d'activité mensuel. Le projet avance bien.",
            "Texte manuscrit simulé : Veuillez trouver ci-joint les documents demandés.",
        ]

    def process_image(self, image_path: str) -> Dict:
        """Simule le traitement OCR."""
        logger.info(f"[MAQUETTE] Simulation du traitement OCR pour : {os.path.basename(image_path)}")
        
        # Simuler un petit délai
        time.sleep(0.1) 
        
        return {
            'text': random.choice(self.mock_texts),
            'confidence': random.uniform(0.85, 0.99),
            'engine': 'mock_processor',
            'processing_time': 0.1,
            'error': None
        }
