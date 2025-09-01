// ORIS - Intégration HTMX et interactions avancées

// Configuration HTMX globale
document.addEventListener('DOMContentLoaded', function() {
    // Configuration des événements HTMX
    htmx.config.globalViewTransitions = true;
    htmx.config.useTemplateFragments = true;
    htmx.config.scrollBehavior = 'smooth';
    
    // Indicateur de chargement global
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        showLoadingIndicator();
    });
    
    document.body.addEventListener('htmx:afterRequest', function(evt) {
        hideLoadingIndicator();
        
        // Gestion des erreurs
        if (evt.detail.xhr.status >= 400) {
            ORIS.showNotification('Une erreur est survenue', 'error');
        }
    });
    
    // Réinitialiser les composants après mise à jour HTMX
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        initializeComponents(evt.detail.target);
    });
});

// ============================================================================
// INTERACTIONS HTMX SPÉCIFIQUES
// ============================================================================

// Upload de fichiers avec barre de progression
function initializeFileUpload() {
    const uploadZones = document.querySelectorAll('.upload-zone');
    
    uploadZones.forEach(zone => {
        zone.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('drag-over');
        });
        
        zone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
        });
        
        zone.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                uploadFiles(files, this);
            }
        });
    });
}

function uploadFiles(files, uploadZone) {
    const formData = new FormData();
    const progressBar = uploadZone.querySelector('.upload-progress');
    const progressFill = progressBar.querySelector('.progress-fill');
    const progressText = progressBar.querySelector('.progress-text');
    
    // Ajouter les fichiers au FormData
    Array.from(files).forEach((file, index) => {
        formData.append(`file_${index}`, file);
    });
    
    // Afficher la barre de progression
    progressBar.style.display = 'block';
    
    // Upload avec XMLHttpRequest pour suivre la progression
    const xhr = new XMLHttpRequest();
    
    xhr.upload.addEventListener('progress', function(e) {
        if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            progressFill.style.width = percentComplete + '%';
            progressText.textContent = Math.round(percentComplete) + '%';
        }
    });
    
    xhr.addEventListener('load', function() {
        if (xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            if (response.success) {
                ORIS.showNotification('Fichiers uploadés avec succès', 'success');
                // Actualiser la liste des lots
                htmx.trigger('#batch-list', 'refresh');
            } else {
                ORIS.showNotification(response.message || 'Erreur lors de l\'upload', 'error');
            }
        } else {
            ORIS.showNotification('Erreur lors de l\'upload', 'error');
        }
        
        // Masquer la barre de progression
        setTimeout(() => {
            progressBar.style.display = 'none';
            progressFill.style.width = '0%';
            progressText.textContent = '0%';
        }, 1000);
    });
    
    xhr.addEventListener('error', function() {
        ORIS.showNotification('Erreur lors de l\'upload', 'error');
        progressBar.style.display = 'none';
    });
    
    xhr.open('POST', uploadZone.dataset.uploadUrl);
    xhr.setRequestHeader('X-CSRFToken', document.querySelector('[name=csrfmiddlewaretoken]').value);
    xhr.send(formData);
}

// ============================================================================
// VALIDATION EN TEMPS RÉEL
// ============================================================================

// Validation de documents avec HTMX
function initializeDocumentValidation() {
    const ocrTextAreas = document.querySelectorAll('.ocr-text-editable');
    
    ocrTextAreas.forEach(textarea => {
        let saveTimeout;
        
        textarea.addEventListener('input', function() {
            // Marquer comme modifié
            this.classList.add('modified');
            
            // Sauvegarder automatiquement après 2 secondes d'inactivité
            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(() => {
                autoSaveDocument(this);
            }, 2000);
        });
        
        // Sauvegarder avec Ctrl+S
        textarea.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                autoSaveDocument(this);
            }
        });
    });
}

function autoSaveDocument(textarea) {
    const documentId = textarea.dataset.documentId;
    const content = textarea.value;
    
    fetch(`/document/${documentId}/save/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
        body: JSON.stringify({
            ocr_text: content
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            textarea.classList.remove('modified');
            textarea.classList.add('saved');
            
            // Afficher indicateur de sauvegarde
            showSaveIndicator('Sauvegardé automatiquement');
            
            setTimeout(() => {
                textarea.classList.remove('saved');
            }, 2000);
        } else {
            ORIS.showNotification('Erreur lors de la sauvegarde', 'error');
        }
    })
    .catch(error => {
        ORIS.showNotification('Erreur lors de la sauvegarde', 'error');
    });
}

function showSaveIndicator(message) {
    const indicator = document.createElement('div');
    indicator.className = 'save-indicator';
    indicator.textContent = message;
    indicator.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--primary-medium);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        z-index: 9999;
        font-size: 0.875rem;
        opacity: 0;
        transform: translateY(-10px);
        transition: all 0.3s ease;
    `;
    
    document.body.appendChild(indicator);
    
    // Animation d'apparition
    setTimeout(() => {
        indicator.style.opacity = '1';
        indicator.style.transform = 'translateY(0)';
    }, 10);
    
    // Suppression après 3 secondes
    setTimeout(() => {
        indicator.style.opacity = '0';
        indicator.style.transform = 'translateY(-10px)';
        setTimeout(() => {
            document.body.removeChild(indicator);
        }, 300);
    }, 3000);
}

// ============================================================================
// FILTRES DYNAMIQUES
// ============================================================================

// Filtres avec HTMX et debouncing
function initializeDynamicFilters() {
    const filterInputs = document.querySelectorAll('.filter-input');
    
    filterInputs.forEach(input => {
        let filterTimeout;
        
        input.addEventListener('input', function() {
            clearTimeout(filterTimeout);
            
            // Afficher l'indicateur de chargement
            const filterContainer = this.closest('.filter-container');
            if (filterContainer) {
                filterContainer.classList.add('filtering');
            }
            
            // Déclencher le filtre après 500ms d'inactivité
            filterTimeout = setTimeout(() => {
                htmx.trigger(this, 'filter-change');
            }, 500);
        });
    });
    
    // Gérer la réponse des filtres
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        if (evt.detail.target.classList.contains('filtered-content')) {
            // Masquer l'indicateur de chargement
            const filterContainers = document.querySelectorAll('.filter-container.filtering');
            filterContainers.forEach(container => {
                container.classList.remove('filtering');
            });
            
            // Mettre à jour les compteurs
            updateFilterCounters();
        }
    });
}

function updateFilterCounters() {
    const counters = document.querySelectorAll('[data-count-target]');
    
    counters.forEach(counter => {
        const target = counter.dataset.countTarget;
        const elements = document.querySelectorAll(target);
        counter.textContent = elements.length;
    });
}

// ============================================================================
// NOTIFICATIONS EN TEMPS RÉEL
// ============================================================================

// Polling pour les notifications
function initializeNotifications() {
    // Vérifier les nouvelles notifications toutes les 30 secondes
    setInterval(() => {
        htmx.ajax('GET', '/api/notifications/', {
            target: '#notifications-container',
            swap: 'innerHTML'
        });
    }, 30000);
    
    // WebSocket pour les notifications en temps réel (si disponible)
    if (window.WebSocket) {
        initializeWebSocketNotifications();
    }
}

function initializeWebSocketNotifications() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
    
    const socket = new WebSocket(wsUrl);
    
    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        if (data.type === 'notification') {
            ORIS.showNotification(data.message, data.level);
        } else if (data.type === 'update') {
            // Actualiser une partie de la page
            if (data.target) {
                htmx.ajax('GET', data.url, {
                    target: data.target,
                    swap: 'innerHTML'
                });
            }
        }
    };
    
    socket.onclose = function() {
        // Reconnecter après 5 secondes
        setTimeout(() => {
            initializeWebSocketNotifications();
        }, 5000);
    };
}

// ============================================================================
// GESTION DES MODALS HTMX
// ============================================================================

// Modals dynamiques avec HTMX
function initializeHTMXModals() {
    // Intercepter les liens/boutons qui ouvrent des modals
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        if (evt.detail.target.classList.contains('modal-content')) {
            // Initialiser les composants dans la modal
            initializeComponents(evt.detail.target);
            
            // Ouvrir la modal
            const modal = evt.detail.target.closest('.modal');
            if (modal) {
                new bootstrap.Modal(modal).show();
            }
        }
    });
    
    // Fermer les modals après soumission réussie
    document.body.addEventListener('htmx:afterRequest', function(evt) {
        if (evt.detail.xhr.status === 200 && evt.detail.target.closest('.modal')) {
            const response = JSON.parse(evt.detail.xhr.responseText);
            if (response.success && response.close_modal) {
                const modal = evt.detail.target.closest('.modal');
                bootstrap.Modal.getInstance(modal).hide();
                
                if (response.message) {
                    ORIS.showNotification(response.message, 'success');
                }
                
                // Actualiser la page si nécessaire
                if (response.refresh_target) {
                    htmx.ajax('GET', window.location.href, {
                        target: response.refresh_target,
                        swap: 'innerHTML'
                    });
                }
            }
        }
    });
}

// ============================================================================
// TABLEAUX INTERACTIFS
// ============================================================================

// Tri et pagination avec HTMX
function initializeInteractiveTables() {
    const tables = document.querySelectorAll('.interactive-table');
    
    tables.forEach(table => {
        // Tri des colonnes
        const sortHeaders = table.querySelectorAll('[data-sort]');
        sortHeaders.forEach(header => {
            header.addEventListener('click', function() {
                const sortBy = this.dataset.sort;
                const currentOrder = this.dataset.order || 'asc';
                const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
                
                // Mettre à jour l'URL avec les paramètres de tri
                const url = new URL(window.location);
                url.searchParams.set('sort', sortBy);
                url.searchParams.set('order', newOrder);
                
                // Charger les données triées
                htmx.ajax('GET', url.toString(), {
                    target: table,
                    swap: 'outerHTML'
                });
            });
        });
        
        // Sélection multiple
        const selectAll = table.querySelector('.select-all');
        if (selectAll) {
            selectAll.addEventListener('change', function() {
                const checkboxes = table.querySelectorAll('.row-select');
                checkboxes.forEach(cb => {
                    cb.checked = this.checked;
                });
                updateBulkActions();
            });
        }
        
        const rowSelects = table.querySelectorAll('.row-select');
        rowSelects.forEach(checkbox => {
            checkbox.addEventListener('change', updateBulkActions);
        });
    });
}

function updateBulkActions() {
    const selectedRows = document.querySelectorAll('.row-select:checked');
    const bulkActions = document.querySelector('.bulk-actions');
    
    if (bulkActions) {
        if (selectedRows.length > 0) {
            bulkActions.classList.add('show');
            bulkActions.querySelector('.selected-count').textContent = selectedRows.length;
        } else {
            bulkActions.classList.remove('show');
        }
    }
}

// ============================================================================
// INITIALISATION
// ============================================================================

// Initialiser tous les composants
function initializeComponents(container = document) {
    initializeFileUpload();
    initializeDocumentValidation();
    initializeDynamicFilters();
    initializeHTMXModals();
    initializeInteractiveTables();
}

// Indicateur de chargement global
function showLoadingIndicator() {
    let indicator = document.getElementById('global-loading');
    
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'global-loading';
        indicator.innerHTML = '<div class="spinner"></div>';
        indicator.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--primary-medium);
            z-index: 9999;
            transform: scaleX(0);
            transform-origin: left;
            transition: transform 0.3s ease;
        `;
        document.body.appendChild(indicator);
    }
    
    indicator.style.transform = 'scaleX(1)';
}

function hideLoadingIndicator() {
    const indicator = document.getElementById('global-loading');
    if (indicator) {
        indicator.style.transform = 'scaleX(0)';
    }
}

// Initialiser au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    initializeComponents();
    initializeNotifications();
});

// Réinitialiser après les mises à jour HTMX
document.body.addEventListener('htmx:afterSwap', function(evt) {
    initializeComponents(evt.detail.target);
});

