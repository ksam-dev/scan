import logging
import os
from typing import List, Dict
from unstructured.partition.auto import partition
from unstructured.cleaners.core import clean
from django.conf import settings

logger = logging.getLogger(__name__)

class DocumentAnalyzer:
    """
    Analyse la structure complète d'un document, en extrayant le texte,
    les tableaux, les titres et d'autres éléments.
    """

    def analyze_document(self, file_path: str) -> List[Dict]:
        """
        Analyse un fichier (PDF ou image) et retourne une liste structurée d'éléments.
        
        Args:
            file_path: Chemin vers le fichier à analyser.
            
        Returns:
            Une liste de dictionnaires, où chaque dictionnaire représente un élément
            (paragraphe, titre, tableau, etc.).
        """
        logger.info(f"Début de l'analyse de la mise en page pour : {os.path.basename(file_path)}")
        
        try:
            # 'partition' est la fonction magique de 'unstructured'.
            # Elle détecte le type de fichier et applique la meilleure stratégie.
            # 'strategy="hi_res"' active des modèles de détection plus précis.
            elements = partition(filename=file_path, strategy="hi_res", model_name="yolox")

            extracted_data = []
            for element in elements:
                # Nettoyer le texte des artefacts courants
                text = clean(element.text, bullets=True, extra_whitespace=True)
                
                element_data = {
                    "type": element.category, # Ex: 'Title', 'NarrativeText', 'ListItem', 'Table'
                    "text": text,
                    "metadata": {
                        "source": os.path.basename(file_path),
                        "page_number": element.metadata.page_number,
                    }
                }

                # Si l'élément est un tableau, extraire sa représentation HTML
                if element.category == "Table":
                    element_data["html_table"] = getattr(element.metadata, 'text_as_html', '')
                    logger.info(f"Tableau détecté à la page {element.metadata.page_number}")

                # Si l'élément est une image (à venir avec des versions plus avancées)
                # if element.category == "Image":
                #     ...

                extracted_data.append(element_data)
            
            logger.info(f"Analyse terminée. {len(extracted_data)} éléments extraits.")
            return extracted_data

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du document {file_path}: {e}", exc_info=True)
            # Retourner une erreur structurée
            return [{
                "type": "Error",
                "text": f"Impossible d'analyser le document. Erreur : {e}",
                "metadata": {}
            }]

