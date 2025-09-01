// ORIS - Système OCR - JavaScript principal

document.addEventListener('DOMContentLoaded', function() {
    // Navigation mobile
    initMobileNavigation();
    
    // Drag & Drop
    initDragAndDrop();
    
    // Tooltips Bootstrap
    initTooltips();
    
    // Animations
    initAnimations();
    
    // HTMX événements
    initHTMXEvents();
});

// Navigation mobile
function initMobileNavigation() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('show');
            if (sidebarOverlay) {
                sidebarOverlay.classList.toggle('show');
            }
        });
    }
    
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            sidebar.classList.remove('show');
            sidebarOverlay.classList.remove('show');
        });
    }
    
    // Fermer sidebar sur clic d'un lien (mobile)
    const sidebarLinks = document.querySelectorAll('.sidebar .nav-link');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('show');
                if (sidebarOverlay) {
                    sidebarOverlay.classList.remove('show');
                }
            }
        });
    });
}

// Drag & Drop pour upload de fichiers
function initDragAndDrop() {
    const dropZones = document.querySelectorAll('.drag-drop-zone');
    
    dropZones.forEach(zone => {
        const fileInput = zone.querySelector('input[type="file"]');
        
        zone.addEventListener('dragover', function(e) {
            e.preventDefault();
            zone.classList.add('dragover');
        });
        
        zone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            zone.classList.remove('dragover');
        });
        
        zone.addEventListener('drop', function(e) {
            e.preventDefault();
            zone.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (fileInput && files.length > 0) {
                fileInput.files = files;
                handleFileUpload(files, zone);
            }
        });
        
        zone.addEventListener('click', function() {
            if (fileInput) {
                fileInput.click();
            }
        });
        
        if (fileInput) {
            fileInput.addEventListener('change', function() {
                handleFileUpload(this.files, zone);
            });
        }
    });
}

// Gestion de l'upload de fichiers
function handleFileUpload(files, zone) {
    const fileList = zone.querySelector('.file-list');
    if (!fileList) return;
    
    fileList.innerHTML = '';
    
    Array.from(files).forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item d-flex justify-content-between align-items-center p-2 mb-2 bg-light rounded';
        
        fileItem.innerHTML = `
            <div class="file-info">
                <i class="fas fa-file-alt me-2 text-primary"></i>
                <span class="file-name">${file.name}</span>
                <small class="text-muted ms-2">(${formatFileSize(file.size)})</small>
            </div>
            <div class="file-actions">
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeFile(this, ${index})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        fileList.appendChild(fileItem);
    });
    
    // Afficher la liste des fichiers
    fileList.style.display = 'block';
}

// Supprimer un fichier de la liste
function removeFile(button, index) {
    const fileItem = button.closest('.file-item');
    fileItem.remove();
    
    // Mettre à jour l'input file si nécessaire
    // Note: Il n'est pas possible de modifier directement files, 
    // il faudrait utiliser FormData pour la soumission
}

// Formater la taille des fichiers
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Initialiser les tooltips Bootstrap
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Animations au scroll
function initAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
            }
        });
    }, observerOptions);
    
    // Observer les cartes et éléments animables
    const animatableElements = document.querySelectorAll('.card-oris, .table-oris');
    animatableElements.forEach(el => {
        observer.observe(el);
    });
}

// Événements HTMX
function initHTMXEvents() {
    // Avant une requête HTMX
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        // Afficher un indicateur de chargement
        showLoadingIndicator(evt.target);
    });
    
    // Après une requête HTMX
    document.body.addEventListener('htmx:afterRequest', function(evt) {
        // Masquer l'indicateur de chargement
        hideLoadingIndicator(evt.target);
        
        // Réinitialiser les tooltips
        initTooltips();
    });
    
    // Erreur HTMX
    document.body.addEventListener('htmx:responseError', function(evt) {
        hideLoadingIndicator(evt.target);
        showNotification('Erreur lors de la requête', 'error');
    });
}

// Indicateur de chargement
function showLoadingIndicator(element) {
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner position-absolute top-50 start-50 translate-middle';
    spinner.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Chargement...</span></div>';
    
    element.style.position = 'relative';
    element.appendChild(spinner);
}

function hideLoadingIndicator(element) {
    const spinner = element.querySelector('.loading-spinner');
    if (spinner) {
        spinner.remove();
    }
}

// Notifications
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-suppression après 5 secondes
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Utilitaires pour les modales
function openModal(modalId) {
    const modal = new bootstrap.Modal(document.getElementById(modalId));
    modal.show();
}

function closeModal(modalId) {
    const modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
    if (modal) {
        modal.hide();
    }
}

// Confirmation d'actions
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Copier dans le presse-papiers
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showNotification('Copié dans le presse-papiers', 'success');
    }).catch(function() {
        showNotification('Erreur lors de la copie', 'error');
    });
}

// Validation de formulaires
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// Export des fonctions globales
window.ORIS = {
    showNotification,
    openModal,
    closeModal,
    confirmAction,
    copyToClipboard,
    validateForm
};

