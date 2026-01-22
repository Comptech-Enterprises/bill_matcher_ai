// Bill Matcher Application JavaScript

const API_BASE_URL = 'http://localhost:5000/api';

// Application State
let state = {
    sessionId: null,
    purchaseFiles: [],
    saleFiles: [],
    purchaseItems: [],
    saleItems: [],
    matchedResults: null,
    summary: null,
    currentStep: 1
};

// DOM Elements
const elements = {
    sessionStatus: document.getElementById('session-status'),
    sessionIdDisplay: document.getElementById('session-id-display'),
    purchaseFileInput: document.getElementById('purchase-file'),
    saleFileInput: document.getElementById('sale-file'),
    purchaseFilesList: document.getElementById('purchase-files-list'),
    saleFilesList: document.getElementById('sale-files-list'),
    processBtn: document.getElementById('process-btn'),
    matchBtn: document.getElementById('match-btn'),
    exportBtn: document.getElementById('export-btn'),
    loadingOverlay: document.getElementById('loading-overlay'),
    loadingMessage: document.getElementById('loading-message'),
    toastContainer: document.getElementById('toast-container'),
    addItemModal: document.getElementById('add-item-modal'),
    addItemForm: document.getElementById('add-item-form')
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    createSession();
});

// Event Listeners
function initializeEventListeners() {
    // File inputs
    elements.purchaseFileInput.addEventListener('change', (e) => handleFileSelect(e, 'purchase'));
    elements.saleFileInput.addEventListener('change', (e) => handleFileSelect(e, 'sale'));

    // Drag and drop
    setupDragAndDrop('purchase-upload', 'purchase');
    setupDragAndDrop('sale-upload', 'sale');

    // Buttons
    elements.processBtn.addEventListener('click', processBills);
    elements.matchBtn.addEventListener('click', matchItems);
    elements.exportBtn.addEventListener('click', exportResults);

    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Modal form
    elements.addItemForm.addEventListener('submit', handleAddItem);
}

// Session Management
async function createSession() {
    try {
        const response = await fetch(`${API_BASE_URL}/session/create`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.session_id) {
            state.sessionId = data.session_id;
            elements.sessionStatus.classList.remove('hidden');
            elements.sessionIdDisplay.textContent = `Session: ${data.session_id.substring(0, 8)}...`;
            showToast('Session created successfully', 'success');
        }
    } catch (error) {
        showToast('Failed to create session. Is the server running?', 'error');
        console.error('Session creation error:', error);
    }
}

async function startNewSession() {
    // Reset state
    state = {
        sessionId: null,
        purchaseFiles: [],
        saleFiles: [],
        purchaseItems: [],
        saleItems: [],
        matchedResults: null,
        summary: null,
        currentStep: 1
    };

    // Reset UI
    elements.purchaseFilesList.innerHTML = '';
    elements.saleFilesList.innerHTML = '';
    elements.purchaseFileInput.value = '';
    elements.saleFileInput.value = '';
    updateProcessButton();
    goToStep(1);

    // Create new session
    await createSession();
}

// File Handling
function handleFileSelect(event, type) {
    const files = Array.from(event.target.files);
    if (type === 'purchase') {
        state.purchaseFiles = [...state.purchaseFiles, ...files];
        renderFilesList(state.purchaseFiles, elements.purchaseFilesList, 'purchase');
    } else {
        state.saleFiles = [...state.saleFiles, ...files];
        renderFilesList(state.saleFiles, elements.saleFilesList, 'sale');
    }
    updateProcessButton();
}

function renderFilesList(files, container, type) {
    container.innerHTML = files.map((file, index) => `
        <div class="file-item">
            <span class="file-name">📄 ${file.name}</span>
            <button class="remove-file" onclick="removeFile('${type}', ${index})">×</button>
        </div>
    `).join('');
}

function removeFile(type, index) {
    if (type === 'purchase') {
        state.purchaseFiles.splice(index, 1);
        renderFilesList(state.purchaseFiles, elements.purchaseFilesList, 'purchase');
    } else {
        state.saleFiles.splice(index, 1);
        renderFilesList(state.saleFiles, elements.saleFilesList, 'sale');
    }
    updateProcessButton();
}

function updateProcessButton() {
    elements.processBtn.disabled = state.purchaseFiles.length === 0 && state.saleFiles.length === 0;
}

// Drag and Drop
function setupDragAndDrop(elementId, type) {
    const element = document.getElementById(elementId);
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        element.addEventListener(eventName, preventDefaults);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        element.addEventListener(eventName, () => element.classList.add('dragover'));
    });

    ['dragleave', 'drop'].forEach(eventName => {
        element.addEventListener(eventName, () => element.classList.remove('dragover'));
    });

    element.addEventListener('drop', (e) => {
        const files = Array.from(e.dataTransfer.files);
        const validFiles = files.filter(file => isValidFile(file));
        
        if (validFiles.length !== files.length) {
            showToast('Some files were skipped (invalid format)', 'warning');
        }
        
        if (type === 'purchase') {
            state.purchaseFiles = [...state.purchaseFiles, ...validFiles];
            renderFilesList(state.purchaseFiles, elements.purchaseFilesList, 'purchase');
        } else {
            state.saleFiles = [...state.saleFiles, ...validFiles];
            renderFilesList(state.saleFiles, elements.saleFilesList, 'sale');
        }
        updateProcessButton();
    });
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function isValidFile(file) {
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];
    return validTypes.includes(file.type);
}

// Bill Processing
async function processBills() {
    if (!state.sessionId) {
        showToast('No active session. Please refresh the page.', 'error');
        return;
    }

    showLoading('Processing bills...');

    try {
        // Process purchase files
        for (const file of state.purchaseFiles) {
            await uploadFile(file, 'purchase');
        }

        // Process sale files
        for (const file of state.saleFiles) {
            await uploadFile(file, 'sale');
        }

        // Fetch updated session data
        await fetchSessionData();

        hideLoading();
        showToast('Bills processed successfully!', 'success');
        goToStep(2);

    } catch (error) {
        hideLoading();
        showToast(`Error processing bills: ${error.message}`, 'error');
        console.error('Processing error:', error);
    }
}

async function uploadFile(file, type) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', state.sessionId);

    const response = await fetch(`${API_BASE_URL}/upload/${type}`, {
        method: 'POST',
        body: formData
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Upload failed');
    }

    const data = await response.json();
    return data;
}

async function fetchSessionData() {
    const response = await fetch(`${API_BASE_URL}/session/${state.sessionId}`);
    const data = await response.json();

    state.purchaseItems = data.purchase_items || [];
    state.saleItems = data.sale_items || [];

    renderItems();
}

// Item Rendering
function renderItems() {
    renderItemsList(state.purchaseItems, 'purchase-items', 'purchase');
    renderItemsList(state.saleItems, 'sale-items', 'sale');
    
    document.getElementById('purchase-count').textContent = state.purchaseItems.length;
    document.getElementById('sale-count').textContent = state.saleItems.length;
}

function renderItemsList(items, containerId, type) {
    const container = document.getElementById(containerId);
    const priceKey = type === 'purchase' ? 'purchase_price' : 'sale_price';

    if (items.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 2rem;">No items found</p>';
        return;
    }

    container.innerHTML = items.map((item, index) => `
        <div class="item-card">
            <div class="item-header">
                <span class="item-name">${item.item_name || 'Unknown Item'}</span>
                <div class="item-actions">
                    <button onclick="editItem('${type}', ${index})" title="Edit">✏️</button>
                    <button onclick="deleteItem('${type}', ${index})" title="Delete">🗑️</button>
                </div>
            </div>
            <div class="item-details">
                <span>S/N: ${item.serial_number || 'N/A'}</span>
                <span>HSN: ${item.hsn_code || 'N/A'}</span>
                <span class="item-price">₹${formatNumber(item[priceKey] || 0)}</span>
            </div>
        </div>
    `).join('');
}

// Item CRUD Operations
function addItem(type) {
    document.getElementById('modal-item-type').value = type;
    document.getElementById('modal-serial').value = '';
    document.getElementById('modal-name').value = '';
    document.getElementById('modal-hsn').value = '';
    document.getElementById('modal-price').value = '';
    elements.addItemModal.classList.remove('hidden');
}

async function handleAddItem(e) {
    e.preventDefault();

    const type = document.getElementById('modal-item-type').value;
    const priceKey = type === 'purchase' ? 'purchase_price' : 'sale_price';

    const item = {
        serial_number: document.getElementById('modal-serial').value || null,
        item_name: document.getElementById('modal-name').value,
        hsn_code: document.getElementById('modal-hsn').value || null,
        [priceKey]: parseFloat(document.getElementById('modal-price').value)
    };

    try {
        const response = await fetch(`${API_BASE_URL}/items/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: state.sessionId,
                item_type: type,
                item: item
            })
        });

        if (!response.ok) throw new Error('Failed to add item');

        if (type === 'purchase') {
            state.purchaseItems.push(item);
        } else {
            state.saleItems.push(item);
        }

        renderItems();
        closeModal();
        showToast('Item added successfully', 'success');

    } catch (error) {
        showToast(`Error adding item: ${error.message}`, 'error');
    }
}

function editItem(type, index) {
    const items = type === 'purchase' ? state.purchaseItems : state.saleItems;
    const item = items[index];
    const priceKey = type === 'purchase' ? 'purchase_price' : 'sale_price';

    document.getElementById('modal-item-type').value = type;
    document.getElementById('modal-serial').value = item.serial_number || '';
    document.getElementById('modal-name').value = item.item_name || '';
    document.getElementById('modal-hsn').value = item.hsn_code || '';
    document.getElementById('modal-price').value = item[priceKey] || '';

    // Change form to update mode
    elements.addItemForm.onsubmit = async (e) => {
        e.preventDefault();
        await updateItem(type, index);
    };

    elements.addItemModal.classList.remove('hidden');
}

async function updateItem(type, index) {
    const priceKey = type === 'purchase' ? 'purchase_price' : 'sale_price';

    const updates = {
        serial_number: document.getElementById('modal-serial').value || null,
        item_name: document.getElementById('modal-name').value,
        hsn_code: document.getElementById('modal-hsn').value || null,
        [priceKey]: parseFloat(document.getElementById('modal-price').value)
    };

    try {
        const response = await fetch(`${API_BASE_URL}/items/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: state.sessionId,
                item_type: type,
                item_index: index,
                updates: updates
            })
        });

        if (!response.ok) throw new Error('Failed to update item');

        if (type === 'purchase') {
            state.purchaseItems[index] = { ...state.purchaseItems[index], ...updates };
        } else {
            state.saleItems[index] = { ...state.saleItems[index], ...updates };
        }

        renderItems();
        closeModal();
        
        // Reset form handler
        elements.addItemForm.onsubmit = handleAddItem;
        
        showToast('Item updated successfully', 'success');

    } catch (error) {
        showToast(`Error updating item: ${error.message}`, 'error');
    }
}

async function deleteItem(type, index) {
    if (!confirm('Are you sure you want to delete this item?')) return;

    try {
        const response = await fetch(`${API_BASE_URL}/items/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: state.sessionId,
                item_type: type,
                item_index: index
            })
        });

        if (!response.ok) throw new Error('Failed to delete item');

        if (type === 'purchase') {
            state.purchaseItems.splice(index, 1);
        } else {
            state.saleItems.splice(index, 1);
        }

        renderItems();
        showToast('Item deleted successfully', 'success');

    } catch (error) {
        showToast(`Error deleting item: ${error.message}`, 'error');
    }
}

function closeModal() {
    elements.addItemModal.classList.add('hidden');
    elements.addItemForm.onsubmit = handleAddItem;
}

// Item Matching
async function matchItems() {
    if (state.purchaseItems.length === 0) {
        showToast('Please add at least one purchase item', 'warning');
        return;
    }

    if (state.saleItems.length === 0) {
        showToast('Please add at least one sale item', 'warning');
        return;
    }

    showLoading('Matching items...');

    try {
        const response = await fetch(`${API_BASE_URL}/match`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: state.sessionId })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Matching failed');
        }

        const data = await response.json();
        state.matchedResults = {
            matched: data.matched,
            unmatched_purchases: data.unmatched_purchases,
            unmatched_sales: data.unmatched_sales
        };
        state.summary = data.summary;

        hideLoading();
        renderResults();
        goToStep(3);
        showToast('Items matched successfully!', 'success');

    } catch (error) {
        hideLoading();
        showToast(`Error matching items: ${error.message}`, 'error');
        console.error('Matching error:', error);
    }
}

// Results Rendering
function renderResults() {
    // Summary cards
    document.getElementById('matched-count').textContent = state.summary.total_matched_items;
    document.getElementById('total-purchase').textContent = `₹${formatNumber(state.summary.total_purchase_value)}`;
    document.getElementById('total-sale').textContent = `₹${formatNumber(state.summary.total_sale_value)}`;
    
    const profitLoss = state.summary.total_profit_loss;
    document.getElementById('total-profit-loss').textContent = `${profitLoss >= 0 ? '+' : ''}₹${formatNumber(profitLoss)}`;
    
    const profitLossCard = document.getElementById('profit-loss-card');
    profitLossCard.classList.remove('profit', 'loss');
    profitLossCard.classList.add(profitLoss >= 0 ? 'profit' : 'loss');

    // Tables
    renderMatchedTable(state.matchedResults.matched);
    renderUnmatchedTable(state.matchedResults.unmatched_purchases, 'unmatched-purchase-table', 'purchase_price');
    renderUnmatchedTable(state.matchedResults.unmatched_sales, 'unmatched-sale-table', 'sale_price');
}

function renderMatchedTable(items) {
    const tbody = document.getElementById('matched-items-table');
    
    if (items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No matched items</td></tr>';
        return;
    }

    tbody.innerHTML = items.map((item, index) => {
        const profitClass = item.profit_loss > 0 ? 'profit' : (item.profit_loss < 0 ? 'loss' : '');
        return `
            <tr>
                <td>${index + 1}</td>
                <td>${item.serial_number || 'N/A'}</td>
                <td>${item.item_name || 'Unknown'}</td>
                <td>${item.hsn_code || 'N/A'}</td>
                <td>₹${formatNumber(item.purchase_price)}</td>
                <td>₹${formatNumber(item.sale_price)}</td>
                <td class="${profitClass}">${item.profit_loss >= 0 ? '+' : ''}₹${formatNumber(item.profit_loss)}</td>
                <td class="${profitClass}">${item.profit_loss_percentage.toFixed(1)}%</td>
            </tr>
        `;
    }).join('');
}

function renderUnmatchedTable(items, tableId, priceKey) {
    const tbody = document.getElementById(tableId);
    
    if (items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No unmatched items</td></tr>';
        return;
    }

    tbody.innerHTML = items.map((item, index) => `
        <tr>
            <td>${index + 1}</td>
            <td>${item.serial_number || 'N/A'}</td>
            <td>${item.item_name || 'Unknown'}</td>
            <td>${item.hsn_code || 'N/A'}</td>
            <td>₹${formatNumber(item[priceKey])}</td>
        </tr>
    `).join('');
}

// Tab Switching
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// Export
async function exportResults() {
    if (!state.sessionId || !state.matchedResults) {
        showToast('No results to export', 'warning');
        return;
    }

    showLoading('Generating Excel file...');

    try {
        const response = await fetch(`${API_BASE_URL}/export/${state.sessionId}`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Export failed');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `bill_matching_${state.sessionId.substring(0, 8)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        hideLoading();
        showToast('Excel file downloaded successfully!', 'success');

    } catch (error) {
        hideLoading();
        showToast(`Error exporting: ${error.message}`, 'error');
        console.error('Export error:', error);
    }
}

// Step Navigation
function goToStep(step) {
    state.currentStep = step;

    // Update step indicators
    document.querySelectorAll('.step').forEach((el, index) => {
        el.classList.remove('active', 'completed');
        if (index + 1 === step) {
            el.classList.add('active');
        } else if (index + 1 < step) {
            el.classList.add('completed');
        }
    });

    // Update step content
    document.querySelectorAll('.step-content').forEach((el, index) => {
        el.classList.toggle('active', index + 1 === step);
    });
}

// Loading
function showLoading(message = 'Processing...') {
    elements.loadingMessage.textContent = message;
    elements.loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    elements.loadingOverlay.classList.add('hidden');
}

// Toast Notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };
    
    toast.innerHTML = `<span>${icons[type]}</span> ${message}`;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Utility Functions
function formatNumber(num) {
    return new Intl.NumberFormat('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(num);
}

// Make functions available globally
window.removeFile = removeFile;
window.addItem = addItem;
window.editItem = editItem;
window.deleteItem = deleteItem;
window.closeModal = closeModal;
window.goToStep = goToStep;
window.startNewSession = startNewSession;
