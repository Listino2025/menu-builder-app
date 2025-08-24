/**
 * Menu Builder JavaScript Application
 * Handles drag & drop, AJAX requests, and UI interactions
 */

class MenuBuilder {
    constructor() {
        this.selectedIngredients = [];
        this.totalCost = 0;
        // Check if we're on an ingredients page and skip initialization
        if (this.isIngredientPage()) {
            console.log('App.js debug - Skipping initialization on ingredients page');
            return;
        }
        console.log('App.js debug - Initializing MenuBuilder');
        this.init();
    }
    
    isIngredientPage() {
        const isIngredient = window.location.pathname.includes('/ingredients');
        console.log('App.js debug - Current path:', window.location.pathname);
        console.log('App.js debug - Is ingredient page:', isIngredient);
        return isIngredient;
    }

    init() {
        this.setupEventListeners();
        this.setupDragAndDrop();
        this.setupFormValidation();
        this.updateActiveNavigation();
        this.setupTooltips();
        this.setupAutoSave();
    }

    setupEventListeners() {
        // Search functionality
        const searchInputs = document.querySelectorAll('[data-search]');
        searchInputs.forEach(input => {
            input.addEventListener('input', this.debounce(this.handleSearch.bind(this), 300));
        });

        // Filter functionality
        const filterSelects = document.querySelectorAll('[data-filter]');
        filterSelects.forEach(select => {
            select.addEventListener('change', this.handleFilter.bind(this));
        });

        // Form submission handlers
        const forms = document.querySelectorAll('form[data-ajax]');
        forms.forEach(form => {
            form.addEventListener('submit', this.handleAjaxForm.bind(this));
        });

        // Ingredient selection
        const ingredientCards = document.querySelectorAll('.ingredient-card');
        ingredientCards.forEach(card => {
            card.addEventListener('click', this.handleIngredientSelect.bind(this));
        });

        // Cost calculation triggers
        const priceInputs = document.querySelectorAll('[data-calculate-cost]');
        priceInputs.forEach(input => {
            input.addEventListener('input', this.calculateCosts.bind(this));
        });

        // Mobile menu toggle
        const mobileNavLinks = document.querySelectorAll('.mobile-nav-link');
        mobileNavLinks.forEach(link => {
            link.addEventListener('click', this.updateMobileNav.bind(this));
        });
    }

    setupDragAndDrop() {
        // Ingredients list (draggable)
        const ingredientsList = document.getElementById('ingredients-list');
        if (ingredientsList) {
            new Sortable(ingredientsList, {
                group: {
                    name: 'ingredients',
                    pull: 'clone',
                    put: false
                },
                sort: false,
                handle: '.drag-handle',
                animation: 150,
                onEnd: this.handleIngredientDrop.bind(this)
            });
        }

        // Sandwich builder (droppable)
        const sandwichBuilder = document.getElementById('sandwich-builder');
        if (sandwichBuilder) {
            new Sortable(sandwichBuilder, {
                group: {
                    name: 'ingredients',
                    pull: false,
                    put: true
                },
                animation: 150,
                onAdd: this.handleIngredientAdd.bind(this),
                onUpdate: this.handleLayerReorder.bind(this),
                onRemove: this.handleIngredientRemove.bind(this)
            });
        }

        // Menu components
        const menuComponents = document.querySelectorAll('.menu-component');
        menuComponents.forEach(component => {
            new Sortable(component, {
                group: 'menu-items',
                animation: 150,
                onEnd: this.calculateMenuCost.bind(this)
            });
        });
    }

    setupFormValidation() {
        // Bootstrap form validation
        const forms = document.querySelectorAll('.needs-validation');
        forms.forEach(form => {
            form.addEventListener('submit', (event) => {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            });
        });

        // Custom validation rules
        const priceInputs = document.querySelectorAll('input[type="number"][step="0.01"]');
        priceInputs.forEach(input => {
            input.addEventListener('blur', this.validatePrice.bind(this));
        });

        // Password strength validation
        const passwordInputs = document.querySelectorAll('input[type="password"][data-strength]');
        passwordInputs.forEach(input => {
            input.addEventListener('input', this.checkPasswordStrength.bind(this));
        });
    }

    updateActiveNavigation() {
        const currentPath = window.location.pathname;
        
        // Desktop navigation
        const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
        navLinks.forEach(link => {
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
            }
        });

        // Mobile navigation
        const mobileLinks = document.querySelectorAll('.mobile-nav-link');
        mobileLinks.forEach(link => {
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
            }
        });
    }

    setupTooltips() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    setupAutoSave() {
        // Auto-save form data to localStorage
        const autoSaveForms = document.querySelectorAll('[data-autosave]');
        autoSaveForms.forEach(form => {
            const formId = form.id || form.getAttribute('data-autosave');
            
            // Load saved data
            this.loadFormData(form, formId);
            
            // Save on input
            form.addEventListener('input', this.debounce(() => {
                this.saveFormData(form, formId);
            }, 1000));
        });
    }

    // Event Handlers
    handleSearch(event) {
        const searchTerm = event.target.value.toLowerCase();
        const searchTarget = event.target.getAttribute('data-search');
        const items = document.querySelectorAll(`[data-searchable="${searchTarget}"]`);

        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (text.includes(searchTerm)) {
                item.style.display = '';
                item.classList.remove('d-none');
            } else {
                item.style.display = 'none';
                item.classList.add('d-none');
            }
        });

        this.updateSearchResults(items, searchTerm);
    }

    handleFilter(event) {
        const filterValue = event.target.value;
        const filterTarget = event.target.getAttribute('data-filter');
        const items = document.querySelectorAll(`[data-filterable="${filterTarget}"]`);

        items.forEach(item => {
            const itemValue = item.getAttribute('data-filter-value');
            if (!filterValue || itemValue === filterValue) {
                item.style.display = '';
                item.classList.remove('d-none');
            } else {
                item.style.display = 'none';
                item.classList.add('d-none');
            }
        });
    }

    handleAjaxForm(event) {
        event.preventDefault();
        const form = event.target;
        const formData = new FormData(form);
        const url = form.action;
        const method = form.method || 'POST';

        this.showLoading(form);

        fetch(url, {
            method: method,
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            this.hideLoading(form);
            this.handleAjaxResponse(data, form);
        })
        .catch(error => {
            this.hideLoading(form);
            this.showError('An error occurred. Please try again.');
            console.error('Ajax error:', error);
        });
    }

    handleIngredientSelect(event) {
        const card = event.currentTarget;
        const ingredientId = card.getAttribute('data-ingredient-id');
        
        if (card.classList.contains('selected')) {
            this.removeIngredient(ingredientId);
            card.classList.remove('selected');
        } else {
            this.addIngredient(ingredientId);
            card.classList.add('selected');
        }
    }

    handleIngredientDrop(event) {
        const item = event.item;
        const ingredientId = item.getAttribute('data-ingredient-id');
        
        if (event.to.id === 'sandwich-builder') {
            this.addIngredientToSandwich(ingredientId);
        }
    }

    handleIngredientAdd(event) {
        const item = event.item;
        const ingredientId = item.getAttribute('data-ingredient-id');
        this.addIngredientToSandwich(ingredientId);
        this.calculateCosts();
    }

    handleIngredientRemove(event) {
        const item = event.item;
        const ingredientId = item.getAttribute('data-ingredient-id');
        this.removeIngredientFromSandwich(ingredientId);
        this.calculateCosts();
    }

    handleLayerReorder(event) {
        this.updateSandwichPreview();
        this.saveCurrentState();
    }

    // Ingredient Management
    addIngredient(ingredientId) {
        if (!this.selectedIngredients.includes(ingredientId)) {
            this.selectedIngredients.push(ingredientId);
            this.updateSelectedCount();
        }
    }

    removeIngredient(ingredientId) {
        const index = this.selectedIngredients.indexOf(ingredientId);
        if (index > -1) {
            this.selectedIngredients.splice(index, 1);
            this.updateSelectedCount();
        }
    }

    addIngredientToSandwich(ingredientId) {
        const ingredient = this.getIngredientData(ingredientId);
        if (!ingredient) return;

        // Check if ingredient is already added
        const existingLayer = document.querySelector(`[data-ingredient-id="${ingredientId}"]`);
        if (existingLayer) {
            return; // Don't add duplicate ingredients
        }
        
        // Create ingredient layer
        const layer = this.createIngredientLayer(ingredient);

        const sandwichBuilder = document.getElementById('sandwich-builder');
        
        // Remove empty state if exists
        const dropZone = sandwichBuilder.querySelector('.drop-zone');
        if (dropZone) {
            dropZone.remove();
        }
        
        sandwichBuilder.appendChild(layer);
        this.updateSandwichPreview();
        this.updateIngredientInputs();
        this.calculateCosts();
    }

    getDefaultQuantity(unitType) {
        // Default absolute quantities for easy editing
        const defaultQuantities = {
            'pieces': 1,      // 1 piece (buns, patties, slices)
            'slices': 2,      // 2 slices (cheese, tomato)
            'g': 50,          // 50g (lettuce, onions, meat)
            'ml': 20,         // 20ml (sauces)
            'kg': 0.100,      // 100g 
            'l': 0.020,       // 20ml
            'portions': 1     // 1 portion
        };
        return defaultQuantities[unitType] || 1;
    }

    createIngredientLayer(ingredient) {
        // Creating ingredient layer with simplified approach - no quantities, fixed F&P cost
        const layer = document.createElement('div');
        layer.className = `sandwich-layer ${ingredient.category.toLowerCase()}`;
        layer.setAttribute('data-ingredient-id', ingredient.id);
        layer.setAttribute('data-ingredient-fp-cost', ingredient.fpCost);
        
        layer.innerHTML = `
            <div class="d-flex align-items-center justify-content-between">
                <div class="flex-grow-1">
                    <div class="fw-medium">${ingredient.name}</div>
                    <small class="text-muted">€${parseFloat(ingredient.fpCost).toFixed(3)} F&P</small>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <button type="button" class="btn btn-sm btn-outline-danger layer-remove">
                        <i class="bi bi-x"></i>
                    </button>
                </div>
            </div>
        `;
        
        // Add event listener for remove button
        const removeBtn = layer.querySelector('.layer-remove');
        removeBtn.addEventListener('click', (e) => {
            this.removeLayer(e.target);
        });
        
        return layer;
    }


    removeLayer(button) {
        const layer = button.closest('.sandwich-layer');
        layer.remove();
        this.updateSandwichPreview();
        this.updateIngredientInputs();
        this.calculateCosts();
        
        // Show empty state if no layers
        const sandwichBuilder = document.getElementById('sandwich-builder');
        if (sandwichBuilder.children.length === 0) {
            this.showEmptyState(sandwichBuilder);
        }
    }

    showEmptyState(container) {
        const dropZone = document.createElement('div');
        dropZone.className = 'drop-zone text-center p-4';
        dropZone.innerHTML = `
            <i class="bi bi-plus-circle display-6 text-muted"></i>
            <p class="text-muted mt-2 mb-0">
                Rilascia gli ingredienti qui o usa il pulsante +
            </p>
        `;
        container.appendChild(dropZone);
    }

    removeIngredientFromSandwich(ingredientId) {
        const layer = document.querySelector(`[data-ingredient-id="${ingredientId}"]`);
        if (layer) {
            layer.remove();
            this.updateSandwichPreview();
            this.calculateCosts();
        }
    }


    // Cost Calculations
    calculateCosts() {
        const layers = document.querySelectorAll('.sandwich-layer');
        let totalCost = 0;

        layers.forEach(layer => {
            const fpCost = parseFloat(layer.getAttribute('data-ingredient-fp-cost')) || 0;
            totalCost += fpCost;
        });

        this.totalCost = totalCost;
        this.updateCostDisplay();
        this.updateIngredientInputs();
    }

    updateIngredientInputs() {
        const ingredientInputsContainer = document.getElementById('ingredient-inputs');
        if (!ingredientInputsContainer) return;

        // Clear existing inputs
        ingredientInputsContainer.innerHTML = '';

        // Add hidden inputs for each ingredient
        const layers = document.querySelectorAll('.sandwich-layer');
        layers.forEach((layer, index) => {
            const ingredientId = layer.getAttribute('data-ingredient-id');

            // Create inputs in the format expected by the backend
            const hiddenInputs = `
                <input type="hidden" name="ingredient_ids[]" value="${ingredientId}">
            `;
            
            ingredientInputsContainer.insertAdjacentHTML('beforeend', hiddenInputs);
        });
    }

    calculateProfit() {
        const sellingPriceInput = document.getElementById('selling_price');
        if (!sellingPriceInput) return;

        const sellingPrice = parseFloat(sellingPriceInput.value) || 0;
        const grossProfit = sellingPrice - this.totalCost;
        const profitPercentage = sellingPrice > 0 ? (grossProfit / sellingPrice) * 100 : 0;

        this.updateProfitDisplay(grossProfit, profitPercentage);
    }

    calculateMenuCost() {
        // Calculate total menu cost including sandwich, fries, drink
        let menuCost = this.totalCost; // Sandwich cost

        const friesSelect = document.getElementById('fries_size');
        const drinkSelect = document.getElementById('drink_size');

        if (friesSelect && friesSelect.value) {
            menuCost += this.getFriesPrice(friesSelect.value);
        }

        if (drinkSelect && drinkSelect.value) {
            menuCost += this.getDrinkPrice(drinkSelect.value);
        }

        this.updateMenuCostDisplay(menuCost);
    }

    // UI Updates
    updateCostDisplay() {
        const costDisplay = document.getElementById('total-cost');
        if (costDisplay) {
            costDisplay.textContent = `€${this.totalCost.toFixed(3)}`;
        }

        const costInput = document.getElementById('total_cost');
        if (costInput) {
            costInput.value = this.totalCost.toFixed(3);
        }
    }

    updateProfitDisplay(profit, percentage) {
        const profitDisplay = document.getElementById('gross-profit');
        const percentageDisplay = document.getElementById('profit-percentage');

        if (profitDisplay) {
            profitDisplay.textContent = `€${profit.toFixed(2)}`;
            profitDisplay.className = `profit-display ${profit >= 0 ? 'text-success' : 'text-danger'}`;
        }

        if (percentageDisplay) {
            percentageDisplay.textContent = `${percentage.toFixed(1)}%`;
            percentageDisplay.className = `${percentage >= 0 ? 'text-success' : 'text-danger'}`;
        }

        // Update hidden form fields
        const profitInput = document.getElementById('gross_profit');
        const percentInput = document.getElementById('gross_profit_percent');
        
        if (profitInput) profitInput.value = profit.toFixed(2);
        if (percentInput) percentInput.value = percentage.toFixed(2);
    }

    updateMenuCostDisplay(cost) {
        const menuCostDisplay = document.getElementById('menu-total-cost');
        if (menuCostDisplay) {
            menuCostDisplay.textContent = `€${cost.toFixed(2)}`;
        }
    }

    updateSelectedCount() {
        const countDisplay = document.getElementById('selected-count');
        if (countDisplay) {
            countDisplay.textContent = this.selectedIngredients.length;
        }
    }

    updateSandwichPreview() {
        // Update visual sandwich preview
        const preview = document.getElementById('sandwich-preview');
        if (!preview) return;

        const layers = document.querySelectorAll('.sandwich-layer');
        let previewHTML = '<div class="sandwich-visual">';

        // Add bun top
        previewHTML += '<div class="bun-top">🍞</div>';

        // Add ingredient layers
        layers.forEach(layer => {
            const category = layer.className.match(/\b(base|protein|cheese|vegetable|sauce)\b/)[0];
            const emoji = this.getCategoryEmoji(category);
            previewHTML += `<div class="layer ${category}">${emoji}</div>`;
        });

        // Add bun bottom
        previewHTML += '<div class="bun-bottom">🍞</div>';
        previewHTML += '</div>';

        preview.innerHTML = previewHTML;
    }

    updateSearchResults(items, searchTerm) {
        const resultsCount = Array.from(items).filter(item => !item.classList.contains('d-none')).length;
        const resultsDisplay = document.getElementById('search-results-count');
        
        if (resultsDisplay) {
            resultsDisplay.textContent = `${resultsCount} result${resultsCount !== 1 ? 's' : ''} found`;
        }
    }

    updateMobileNav(event) {
        const mobileLinks = document.querySelectorAll('.mobile-nav-link');
        mobileLinks.forEach(link => link.classList.remove('active'));
        event.currentTarget.classList.add('active');
    }

    // Utility Functions
    getIngredientData(ingredientId) {
        // Find the ingredient element in the ingredients list
        const ingredientElement = document.querySelector(`[data-ingredient-id="${ingredientId}"]`);
        if (!ingredientElement) {
            console.error('Ingredient element not found for ID:', ingredientId);
            return null;
        }

        const ingredientData = {
            id: ingredientId,
            name: ingredientElement.getAttribute('data-ingredient-name'),
            fpCost: parseFloat(ingredientElement.getAttribute('data-ingredient-fp-cost')),
            category: ingredientElement.getAttribute('data-ingredient-category')
        };
        
        // Ingredient data retrieved
        return ingredientData;
    }

    getCategoryEmoji(category) {
        const emojis = {
            'base': '🍞',
            'protein': '🥩',
            'cheese': '🧀',
            'vegetable': '🥬',
            'sauce': '🥫'
        };
        return emojis[category] || '🔸';
    }

    getFriesPrice(size) {
        const prices = { 'small': 2.50, 'medium': 3.00, 'large': 3.50 };
        return prices[size] || 0;
    }

    getDrinkPrice(size) {
        const prices = { 'small': 1.50, 'medium': 2.00, 'large': 2.50 };
        return prices[size] || 0;
    }

    // Form Utilities
    saveFormData(form, formId) {
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        localStorage.setItem(`form_${formId}`, JSON.stringify(data));
    }

    loadFormData(form, formId) {
        const savedData = localStorage.getItem(`form_${formId}`);
        if (!savedData) return;

        try {
            const data = JSON.parse(savedData);
            Object.keys(data).forEach(key => {
                const input = form.querySelector(`[name="${key}"]`);
                if (input && input.type !== 'file') {
                    input.value = data[key];
                }
            });
        } catch (error) {
            console.error('Error loading form data:', error);
        }
    }

    saveCurrentState() {
        const state = {
            selectedIngredients: this.selectedIngredients,
            totalCost: this.totalCost,
            timestamp: Date.now()
        };
        
        localStorage.setItem('menuBuilder_state', JSON.stringify(state));
    }

    // Validation
    validatePrice(event) {
        const input = event.target;
        const value = parseFloat(input.value);
        
        if (isNaN(value) || value < 0) {
            input.setCustomValidity('Please enter a valid positive number');
        } else {
            input.setCustomValidity('');
        }
    }

    checkPasswordStrength(event) {
        const password = event.target.value;
        const strengthBar = document.getElementById('password-strength');
        if (!strengthBar) return;

        let strength = 0;
        let feedback = [];

        // Length check
        if (password.length >= 8) strength += 1;
        else feedback.push('At least 8 characters');

        // Uppercase check
        if (/[A-Z]/.test(password)) strength += 1;
        else feedback.push('One uppercase letter');

        // Lowercase check
        if (/[a-z]/.test(password)) strength += 1;
        else feedback.push('One lowercase letter');

        // Number check
        if (/\d/.test(password)) strength += 1;
        else feedback.push('One number');

        // Special character check
        if (/[^A-Za-z0-9]/.test(password)) strength += 1;
        else feedback.push('One special character');

        this.updatePasswordStrength(strengthBar, strength, feedback);
    }

    updatePasswordStrength(strengthBar, strength, feedback) {
        const strengthClasses = ['bg-danger', 'bg-warning', 'bg-info', 'bg-success'];
        const strengthTexts = ['Weak', 'Fair', 'Good', 'Strong'];
        
        strengthBar.className = `progress-bar ${strengthClasses[Math.min(strength - 1, 3)]}`;
        strengthBar.style.width = `${(strength / 5) * 100}%`;
        strengthBar.textContent = strength > 0 ? strengthTexts[Math.min(strength - 1, 3)] : '';

        const feedbackDiv = document.getElementById('password-feedback');
        if (feedbackDiv) {
            feedbackDiv.innerHTML = feedback.length > 0 ? 
                `<small class="text-muted">Need: ${feedback.join(', ')}</small>` : 
                '<small class="text-success">Password strength is good!</small>';
        }
    }

    // UI Helpers
    showLoading(element) {
        const button = element.querySelector('button[type="submit"]');
        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
        }
    }

    hideLoading(element) {
        const button = element.querySelector('button[type="submit"]');
        if (button) {
            button.disabled = false;
            button.innerHTML = button.getAttribute('data-original-text') || 'Submit';
        }
    }

    showError(message) {
        this.showAlert(message, 'danger');
    }

    showSuccess(message) {
        this.showAlert(message, 'success');
    }

    showAlert(message, type) {
        const alertContainer = document.getElementById('alert-container') || document.querySelector('.container-fluid');
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertContainer.insertBefore(alert, alertContainer.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }

    handleAjaxResponse(data, form) {
        if (data.success) {
            this.showSuccess(data.message || 'Operation completed successfully');
            if (data.redirect) {
                window.location.href = data.redirect;
            }
        } else {
            this.showError(data.message || 'An error occurred');
        }
    }

    // Utility function for debouncing
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    window.menuBuilder = new MenuBuilder();
    
    // Service Worker registration for PWA
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => console.log('SW registered'))
            .catch(error => console.log('SW registration failed'));
    }
});