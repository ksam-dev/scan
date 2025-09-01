#!/usr/bin/env python3
"""
Code OCR Ultra-Puissant pour ORIS
==================================

Ce script démontre l'utilisation des moteurs OCR/HTR intégrés dans ORIS
pour traiter des documents avec une précision maximale.

Fonctionnalités:
- Détection automatique du type de document (imprimé vs manuscrit)
- Sélection automatique du meilleur moteur OCR/HTR
- Traitement multi-moteurs avec fusion des résultats
- Support des documents multi-pages
- Extraction de champs structurés
- Système de confiance et validation
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ajouter le chemin du projet Django
sys.path.append('/home/ubuntu/oris_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oris.settings')

import django
django.setup()

from ocr.engines import ocr_manager
from documents.models import Document, Page, OCRResult
import cv2
import numpy as np
from PIL import Image
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UltraPowerfulOCR:
    """
    Classe principale pour l'OCR ultra-puissant
    """
    
    def __init__(self):
        self.ocr_manager = ocr_manager
        self.confidence_threshold = 0.7
        self.engines_priority = {
            'printed': ['easyocr', 'tesseract'],
            'handwritten': ['trocr', 'easyocr']
        }
    
    def detect_document_type(self, image_path: str) -> str:
        """
        Détecte si un document est imprimé ou manuscrit
        
        Args:
            image_path: Chemin vers l'image
            
        Returns:
            'printed' ou 'handwritten'
        """
        is_handwritten = self.ocr_manager.detect_handwriting(image_path)
        return 'handwritten' if is_handwritten else 'printed'
    
    def count_pages(self, file_path: str) -> int:
        """
        Compte le nombre de pages d'un document
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            Nombre de pages
        """
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == '.pdf':
            try:
                from pdf2image import convert_from_path
                images = convert_from_path(file_path, first_page=1, last_page=1)
                # Pour compter toutes les pages, on utilise pdfinfo ou PyPDF2
                import PyPDF2
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    return len(pdf_reader.pages)
            except Exception as e:
                logger.error(f"Erreur lors du comptage des pages PDF: {e}")
                return 1
        else:
            # Pour les images, c'est toujours 1 page
            return 1
    
    def extract_pages_from_pdf(self, pdf_path: str, output_dir: str) -> List[str]:
        """
        Extrait les pages d'un PDF en images
        
        Args:
            pdf_path: Chemin vers le PDF
            output_dir: Dossier de sortie
            
        Returns:
            Liste des chemins vers les images extraites
        """
        try:
            from pdf2image import convert_from_path
            
            # Créer le dossier de sortie
            os.makedirs(output_dir, exist_ok=True)
            
            # Convertir le PDF en images
            images = convert_from_path(pdf_path, dpi=300)
            
            page_paths = []
            for i, image in enumerate(images, 1):
                page_path = os.path.join(output_dir, f"page_{i:03d}.png")
                image.save(page_path, 'PNG')
                page_paths.append(page_path)
                logger.info(f"Page {i} extraite: {page_path}")
            
            return page_paths
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des pages: {e}")
            return []
    
    def process_single_image(self, image_path: str, engines: List[str] = None) -> Dict:
        """
        Traite une seule image avec les moteurs OCR spécifiés
        
        Args:
            image_path: Chemin vers l'image
            engines: Liste des moteurs à utiliser (None = auto)
            
        Returns:
            Dictionnaire avec les résultats de tous les moteurs
        """
        results = {}
        
        # Détection automatique du type si pas de moteurs spécifiés
        if engines is None:
            doc_type = self.detect_document_type(image_path)
            engines = self.engines_priority.get(doc_type, ['tesseract'])
            logger.info(f"Document détecté comme: {doc_type}, moteurs: {engines}")
        
        # Traitement avec chaque moteur
        for engine in engines:
            if engine in self.ocr_manager.get_available_engines():
                logger.info(f"Traitement avec {engine}...")
                try:
                    result = self.ocr_manager.process_with_engine(engine, image_path)
                    results[engine] = result
                    logger.info(f"{engine}: {len(result.get('text', ''))} caractères, "
                              f"confiance: {result.get('confidence', 0):.2f}")
                except Exception as e:
                    logger.error(f"Erreur avec {engine}: {e}")
                    results[engine] = {
                        'text': '',
                        'confidence': 0.0,
                        'error': str(e)
                    }
            else:
                logger.warning(f"Moteur {engine} non disponible")
        
        return results
    
    def merge_ocr_results(self, results: Dict) -> Dict:
        """
        Fusionne les résultats de plusieurs moteurs OCR
        
        Args:
            results: Dictionnaire des résultats par moteur
            
        Returns:
            Résultat fusionné optimisé
        """
        if not results:
            return {'text': '', 'confidence': 0.0, 'engine': 'none'}
        
        # Trouver le résultat avec la meilleure confiance
        best_result = None
        best_confidence = 0.0
        best_engine = None
        
        for engine, result in results.items():
            if 'error' not in result:
                confidence = result.get('confidence', 0.0)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_result = result
                    best_engine = engine
        
        if best_result is None:
            # Aucun résultat valide, prendre le premier disponible
            for engine, result in results.items():
                if result.get('text'):
                    best_result = result
                    best_engine = engine
                    break
        
        if best_result is None:
            return {'text': '', 'confidence': 0.0, 'engine': 'none'}
        
        # Enrichir le résultat avec des métadonnées
        merged_result = best_result.copy()
        merged_result['engine'] = best_engine
        merged_result['all_engines'] = list(results.keys())
        merged_result['engine_count'] = len([r for r in results.values() if 'error' not in r])
        
        return merged_result
    
    def extract_structured_fields(self, text: str, document_type: str = None) -> Dict:
        """
        Extrait des champs structurés du texte OCR
        
        Args:
            text: Texte extrait par OCR
            document_type: Type de document (optionnel)
            
        Returns:
            Dictionnaire des champs extraits
        """
        import re
        
        fields = {}
        
        # Extraction de dates
        date_patterns = [
            r'\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b',
            r'\b(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{2,4})\b',
            r'\b(\d{2,4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b'
        ]
        
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, text, re.IGNORECASE))
        
        if dates:
            fields['dates'] = list(set(dates))
        
        # Extraction de numéros (téléphone, SIRET, etc.)
        phone_pattern = r'\b(?:\+33|0)[1-9](?:[0-9]{8})\b'
        phones = re.findall(phone_pattern, text)
        if phones:
            fields['phones'] = phones
        
        # Extraction d'emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            fields['emails'] = emails
        
        # Extraction de montants
        amount_pattern = r'\b(\d+[,\.]?\d*)\s*(?:€|EUR|euros?)\b'
        amounts = re.findall(amount_pattern, text, re.IGNORECASE)
        if amounts:
            fields['amounts'] = amounts
        
        # Statistiques du texte
        fields['stats'] = {
            'character_count': len(text),
            'word_count': len(text.split()),
            'line_count': len(text.split('\n'))
        }
        
        return fields
    
    def process_document(self, file_path: str, output_dir: str = None, engines: List[str] = None) -> Dict:
        """
        Traite un document complet (PDF ou image)
        
        Args:
            file_path: Chemin vers le document
            output_dir: Dossier de sortie (optionnel)
            engines: Moteurs à utiliser (optionnel)
            
        Returns:
            Résultats complets du traitement
        """
        start_time = time.time()
        
        if output_dir is None:
            output_dir = f"output_{int(time.time())}"
        
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Traitement du document: {file_path}")
        
        # Compter les pages
        total_pages = self.count_pages(file_path)
        logger.info(f"Nombre de pages détectées: {total_pages}")
        
        # Extraire les pages si c'est un PDF
        if Path(file_path).suffix.lower() == '.pdf':
            page_paths = self.extract_pages_from_pdf(file_path, output_dir)
        else:
            page_paths = [file_path]
        
        # Traiter chaque page
        page_results = []
        for i, page_path in enumerate(page_paths, 1):
            logger.info(f"Traitement de la page {i}/{len(page_paths)}")
            
            # OCR de la page
            ocr_results = self.process_single_image(page_path, engines)
            
            # Fusion des résultats
            merged_result = self.merge_ocr_results(ocr_results)
            
            # Extraction de champs structurés
            structured_fields = self.extract_structured_fields(merged_result.get('text', ''))
            
            page_result = {
                'page_number': i,
                'image_path': page_path,
                'ocr_results': ocr_results,
                'merged_result': merged_result,
                'structured_fields': structured_fields,
                'processing_time': merged_result.get('processing_time', 0)
            }
            
            page_results.append(page_result)
        
        # Résultats globaux
        total_processing_time = time.time() - start_time
        
        # Fusion de tout le texte
        all_text = '\n\n'.join([
            page['merged_result'].get('text', '') 
            for page in page_results
        ])
        
        # Confiance moyenne
        confidences = [
            page['merged_result'].get('confidence', 0) 
            for page in page_results
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Champs structurés globaux
        global_fields = self.extract_structured_fields(all_text)
        
        final_result = {
            'document_path': file_path,
            'total_pages': total_pages,
            'processed_pages': len(page_results),
            'total_processing_time': total_processing_time,
            'average_confidence': avg_confidence,
            'full_text': all_text,
            'global_structured_fields': global_fields,
            'page_results': page_results,
            'engines_used': list(set([
                page['merged_result'].get('engine', 'unknown') 
                for page in page_results
            ])),
            'output_directory': output_dir
        }
        
        # Sauvegarder les résultats
        results_file = os.path.join(output_dir, 'ocr_results.json')
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Traitement terminé en {total_processing_time:.2f}s")
        logger.info(f"Confiance moyenne: {avg_confidence:.2f}")
        logger.info(f"Résultats sauvegardés dans: {results_file}")
        
        return final_result


def main():
    """Fonction principale pour l'utilisation en ligne de commande"""
    parser = argparse.ArgumentParser(description='OCR Ultra-Puissant pour ORIS')
    parser.add_argument('file_path', help='Chemin vers le document à traiter')
    parser.add_argument('--output', '-o', help='Dossier de sortie')
    parser.add_argument('--engines', '-e', nargs='+', 
                       choices=['tesseract', 'easyocr', 'trocr'],
                       help='Moteurs OCR à utiliser')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Mode verbeux')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Vérifier que le fichier existe
    if not os.path.exists(args.file_path):
        print(f"Erreur: Le fichier {args.file_path} n'existe pas")
        return 1
    
    # Créer l'instance OCR
    ocr = UltraPowerfulOCR()
    
    try:
        # Traiter le document
        results = ocr.process_document(
            file_path=args.file_path,
            output_dir=args.output,
            engines=args.engines
        )
        
        # Afficher un résumé
        print("\n" + "="*60)
        print("RÉSULTATS DU TRAITEMENT OCR ULTRA-PUISSANT")
        print("="*60)
        print(f"Document: {results['document_path']}")
        print(f"Pages traitées: {results['processed_pages']}/{results['total_pages']}")
        print(f"Temps de traitement: {results['total_processing_time']:.2f}s")
        print(f"Confiance moyenne: {results['average_confidence']:.2f}")
        print(f"Moteurs utilisés: {', '.join(results['engines_used'])}")
        print(f"Caractères extraits: {len(results['full_text'])}")
        
        # Afficher les champs structurés
        if results['global_structured_fields']:
            print("\nChamps structurés détectés:")
            for field, value in results['global_structured_fields'].items():
                if field != 'stats':
                    print(f"  {field}: {value}")
        
        print(f"\nRésultats complets sauvegardés dans: {results['output_directory']}")
        
        return 0
        
    except Exception as e:
        print(f"Erreur lors du traitement: {e}")
        logger.exception("Erreur détaillée:")
        return 1


if __name__ == '__main__':
    exit(main())

