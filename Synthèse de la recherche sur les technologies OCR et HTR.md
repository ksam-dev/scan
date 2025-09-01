# Synthèse de la recherche sur les technologies OCR et HTR

## 1. Modèles OCR Open Source

## 2. Modèles HTR Open Source

## 3. Datasets pour l'OCR et le HTR



### Tesseract

*   **Description:** L'un des moteurs OCR open source les plus anciens et les plus utilisés, initialement développé par Hewlett-Packard et maintenant maintenu par Google. Il est très polyvalent et supporte de nombreuses langues.
*   **Avantages:** Large communauté, bien documenté, supporte de nombreuses langues, peut être entraîné sur des données personnalisées.
*   **Inconvénients:** Peut être moins précis sur des documents complexes ou des images de mauvaise qualité, la configuration et l'entraînement peuvent être complexes.

### PaddleOCR

*   **Description:** Un kit d'outils OCR open source développé par Baidu, qui propose des modèles légers et performants pour la détection et la reconnaissance de texte. Il est connu pour sa facilité d'utilisation et ses bonnes performances sur diverses langues, y compris le chinois.
*   **Avantages:** Modèles légers et rapides, bonnes performances, facile à utiliser, supporte plusieurs langues, inclut des modèles pré-entraînés.
*   **Inconvénients:** Peut nécessiter des ressources GPU pour des performances optimales, moins de flexibilité pour des cas d'utilisation très spécifiques par rapport à Tesseract pour l'entraînement personnalisé.

### EasyOCR

*   **Description:** Une bibliothèque Python qui fournit une solution OCR prête à l'emploi pour plus de 80 langues. Elle est conçue pour être facile à intégrer et à utiliser, même pour les débutants.
*   **Avantages:** Très facile à utiliser, supporte un grand nombre de langues, installation simple.
*   **Inconvénients:** Moins de contrôle sur les modèles sous-jacents, peut être moins performant que des solutions plus complexes pour des cas d'utilisation très spécifiques.

### DocTR

*   **Description:** Une bibliothèque Python pour la reconnaissance de texte dans les documents, basée sur des modèles de deep learning de pointe. Elle se concentre sur l'extraction de texte structuré à partir de documents.
*   **Avantages:** Très performant pour l'extraction de texte structuré, utilise des modèles de deep learning récents, facile à intégrer.
*   **Inconvénients:** Peut être plus complexe à mettre en œuvre que EasyOCR, nécessite des connaissances en deep learning pour une personnalisation avancée.

### Kraken

*   **Description:** Un moteur OCR open source axé sur les documents historiques et les écritures non latines. Il est particulièrement utile pour la numérisation de manuscrits et de documents anciens.
*   **Avantages:** Spécialisé dans les documents historiques et manuscrits, flexible pour l'entraînement de modèles personnalisés.
*   **Inconvénients:** Moins généraliste que Tesseract ou PaddleOCR pour les documents imprimés modernes, peut nécessiter un effort d'entraînement important pour des résultats optimaux.

### Surya OCR

*   **Description:** Un moteur OCR open source qui se concentre sur la détection de la mise en page et la reconnaissance de texte. Il est conçu pour être rapide et précis.
*   **Avantages:** Bonne détection de la mise en page, rapide, open source.
*   **Inconvénients:** Moins mature que d'autres solutions comme Tesseract ou PaddleOCR.

**Recommandation pour ORIS (OCR imprimé):**

Pour les documents imprimés, une combinaison de **PaddleOCR** (pour sa performance et sa facilité d'utilisation) et de **Tesseract** (en tant que fallback robuste et pour sa polyvalence linguistique) semble être la meilleure approche. **DocTR** pourrait être envisagé pour l'extraction de données structurées si nécessaire. Le système devra être capable de basculer entre ces moteurs en fonction de la qualité du document et des besoins spécifiques.



## 2. Modèles HTR Open Source

### TrOCR

*   **Description:** Un modèle de reconnaissance de texte manuscrit (HTR) basé sur l'architecture Transformer, développé par Microsoft. Il est conçu pour la reconnaissance de texte de bout en bout à partir d'images.
*   **Avantages:** Performances de pointe, basé sur l'architecture Transformer, supporte la reconnaissance de texte manuscrit.
*   **Inconvénients:** Nécessite des ressources de calcul importantes, peut être complexe à entraîner à partir de zéro.

### Donut

*   **Description:** Un modèle de compréhension de documents sans OCR (Document Understanding Transformer) qui peut être utilisé pour l'extraction d'informations à partir de documents visuels, y compris les documents manuscrits, sans avoir besoin d'une étape OCR explicite.
*   **Avantages:** Approche de bout en bout pour la compréhension de documents, efficace pour l'extraction d'informations structurées, supporte les documents manuscrits.
*   **Inconvénients:** Peut être plus complexe à mettre en œuvre que les modèles HTR traditionnels, nécessite des données d'entraînement spécifiques pour des tâches d'extraction d'informations.

### Kraken

*   **Description:** Mentionné précédemment dans la section OCR, Kraken est également très performant pour la reconnaissance de texte manuscrit, en particulier pour les documents historiques et les écritures non latines. Il permet l'entraînement de modèles personnalisés.
*   **Avantages:** Spécialisé dans les documents historiques et manuscrits, flexible pour l'entraînement de modèles personnalisés, bonne documentation.
*   **Inconvénients:** Nécessite un effort d'entraînement important pour des résultats optimaux sur de nouvelles écritures.

### PyLaia

*   **Description:** Une bibliothèque open source pour la reconnaissance de texte manuscrit, souvent utilisée pour l'entraînement de modèles HTR. Elle est basée sur PyTorch et offre une grande flexibilité pour la recherche et le développement.
*   **Avantages:** Flexible, basé sur PyTorch, adapté à la recherche et au développement de modèles HTR.
*   **Inconvénients:** Peut nécessiter une expertise en PyTorch et en HTR pour une utilisation optimale.

**Recommandation pour ORIS (HTR manuscrit):**

Pour la reconnaissance de texte manuscrit, **TrOCR** est un excellent point de départ en raison de ses performances de pointe. **Kraken** sera essentiel pour les documents historiques ou les écritures très spécifiques nécessitant un entraînement personnalisé. **Donut** pourrait être exploré pour des cas d'utilisation où l'extraction d'informations structurées est primordiale, au-delà de la simple transcription. Le système devra être capable de détecter si un document est imprimé ou manuscrit pour diriger vers le pipeline OCR ou HTR approprié.



## 3. Datasets pour l'OCR et le HTR

### Datasets pour l'OCR (imprimé)

*   **COCO-Text:** Un grand dataset pour la détection et la reconnaissance de texte dans des images de scènes naturelles. Il contient des images avec des instances de texte recadrées.
*   **SynthText:** Un dataset synthétique généré à partir de scènes naturelles, très utile pour l'entraînement de modèles OCR. Il permet de créer une grande quantité de données d'entraînement variées.
*   **ICDAR Datasets:** Une série de datasets créés pour les compétitions de reconnaissance de texte, couvrant divers scénarios (texte en scène, texte de document, etc.).

### Datasets pour le HTR (manuscrit)

*   **IAM Handwriting Database:** L'un des datasets les plus populaires pour l'entraînement et le test de reconnaisseurs de texte manuscrit. Il contient des formulaires de texte anglais manuscrit.
*   **HTR-United:** Un catalogue et un écosystème pour le partage et la recherche de données de vérité terrain pour la reconnaissance optique de caractères ou de texte manuscrit (OCR/HTR). Il référence de nombreux datasets documentés.
*   **READ Dataset:** Un dataset pour la reconnaissance de texte manuscrit historique, souvent utilisé pour évaluer les performances des modèles HTR sur des documents anciens.

**Recommandation pour ORIS (Datasets):**

Pour l'entraînement et l'évaluation des modèles OCR, il sera important d'utiliser une combinaison de datasets réels (comme COCO-Text ou ICDAR) et synthétiques (comme SynthText) pour assurer la robustesse du modèle. Pour le HTR, le **IAM Handwriting Database** est un incontournable. L'exploration de **HTR-United** permettra de découvrir d'autres datasets pertinents pour des écritures spécifiques ou des langues différentes si le besoin se présente. Il sera également crucial de collecter et d'annoter des données spécifiques aux documents que ORIS aura à traiter (registres, documents sensibles, etc.) pour le fine-tuning des modèles et l'amélioration de la précision sur des cas d'usage réels.



## 4. Sélection des modèles et datasets pour ORIS

Pour le projet ORIS, l'objectif est de créer un système OCR/HTR rapide, agile et puissant, capable de numériser des documents imprimés et manuscrits, quelle que soit leur taille.

### Modèles OCR (pour documents imprimés)

*   **Choix principal: PaddleOCR.** Il offre un bon équilibre entre performance, légèreté et facilité d'utilisation. Ses modèles pré-entraînés sont robustes pour une large gamme de documents imprimés.
*   **Fallback/Complémentaire: Tesseract.** En tant que moteur OCR éprouvé et très polyvalent, Tesseract servira de solution de secours si PaddleOCR rencontre des difficultés sur certains types de documents ou de langues. Il peut également être utilisé pour des besoins spécifiques de personnalisation.
*   **Pour l'extraction structurée: DocTR.** Si l'application ORIS nécessite une extraction de données structurées (par exemple, champs spécifiques dans des factures ou des formulaires), DocTR sera une excellente option grâce à son approche basée sur le deep learning pour la compréhension de documents.

### Modèles HTR (pour documents manuscrits)

*   **Choix principal: TrOCR.** Pour la reconnaissance de texte manuscrit, TrOCR est le choix privilégié en raison de ses performances de pointe et de son architecture basée sur les Transformers, qui excelle dans les tâches de séquence à séquence.
*   **Pour les documents historiques/spécifiques: Kraken.** Si ORIS doit traiter des documents manuscrits anciens, des écritures très spécifiques ou des langues moins courantes, Kraken sera indispensable. Sa capacité à être entraîné sur des données personnalisées le rend très flexible pour ces cas d'usage.
*   **Pour la compréhension visuelle: Donut.** Pour les scénarios où la simple transcription ne suffit pas et où une compréhension plus profonde de la structure visuelle du document manuscrit est nécessaire (par exemple, extraire des informations de formulaires manuscrits), Donut sera exploré.

### Datasets pour l'entraînement et le fine-tuning

*   **Pour l'OCR imprimé:**
    *   **SynthText:** Pour générer de grandes quantités de données d'entraînement synthétiques et variées, ce qui est crucial pour la robustesse du modèle.
    *   **COCO-Text / ICDAR:** Pour l'évaluation et le fine-tuning sur des données réelles de scènes naturelles et de documents, assurant que les modèles performent bien dans des conditions réelles.
*   **Pour le HTR manuscrit:**
    *   **IAM Handwriting Database:** C'est le dataset de référence pour l'entraînement et l'évaluation des modèles HTR en anglais. Il sera fondamental pour le développement du pipeline HTR de base.
    *   **HTR-United:** Ce catalogue sera utilisé pour identifier et potentiellement acquérir d'autres datasets pertinents pour des langues ou des styles d'écriture spécifiques, si le projet ORIS s'étend à d'autres types de manuscrits.
*   **Datasets personnalisés:** Il est crucial de prévoir la collecte et l'annotation de données spécifiques aux types de documents que ORIS traitera (registres, documents sensibles, etc.). Le fine-tuning des modèles sur ces données spécifiques sera la clé pour atteindre une précision élevée et répondre aux besoins uniques des utilisateurs d'ORIS.

### Avantages de cette sélection

*   **Performance:** Combinaison de modèles de pointe pour l'OCR et le HTR.
*   **Flexibilité:** Possibilité de basculer entre différents moteurs et d'entraîner des modèles personnalisés.
*   **Robustesse:** Utilisation de datasets variés (synthétiques, réels, manuscrits) pour un entraînement complet.
*   **Open Source:** Adhésion à la demande de l'utilisateur d'utiliser du code open source, permettant une personnalisation et une transparence complètes.

### Inconvénients potentiels et défis

*   **Complexité d'intégration:** L'intégration de plusieurs moteurs OCR/HTR et la gestion de leurs pipelines respectifs peuvent être complexes.
*   **Ressources de calcul:** L'entraînement et l'exécution de modèles de deep learning (TrOCR, Donut, DocTR) nécessitent des ressources GPU significatives.
*   **Qualité des données:** La performance finale dépendra fortement de la qualité et de la pertinence des données d'entraînement, en particulier pour le fine-tuning sur des documents spécifiques à ORIS.
*   **Détection imprimé vs. manuscrit:** La mise en place d'un mécanisme fiable pour détecter automatiquement si un document est imprimé ou manuscrit sera un défi clé pour diriger le document vers le bon pipeline.

Cette phase de recherche a permis d'identifier les technologies clés qui formeront la base du système OCR/HTR d'ORIS. La prochaine étape consistera à configurer l'environnement de développement et à structurer le projet.

