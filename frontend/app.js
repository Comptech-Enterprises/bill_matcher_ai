// Bill Matcher Application JavaScript

// Auto-detect environment: use localhost for dev, production URL for Render
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:5000/api'
    : 'https://bill-matcher-ai.onrender.com/api';

// Application State
let state = {
    // Auth state
    token: localStorage.getItem('auth_token'),
    user: JSON.parse(localStorage.getItem('user_info') || 'null'),
    
    // Session state
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
    // Auth elements
    loginPage: document.getElementById('login-page'),
    mainApp: document.getElementById('main-app'),
    loginForm: document.getElementById('login-form'),
    loginUsername: document.getElementById('login-username'),
    loginPassword: document.getElementById('login-password'),
    loginError: document.getElementById('login-error'),
    userDisplayName: document.getElementById('user-display-name'),
    userMenuBtn: document.getElementById('user-menu-btn'),
    userDropdown: document.getElementById('user-dropdown'),
    changePasswordLink: document.getElementById('change-password-link'),
    adminPanelLink: document.getElementById('admin-panel-link'),
    logoutLink: document.getElementById('logout-link'),
    
    // Change password modal
    changePasswordModal: document.getElementById('change-password-modal'),
    changePasswordForm: document.getElementById('change-password-form'),
    passwordError: document.getElementById('password-error'),
    
    // Admin panel modal
    adminPanelModal: document.getElementById('admin-panel-modal'),
    userFormContainer: document.getElementById('user-form-container'),
    userForm: document.getElementById('user-form'),
    usersTableBody: document.getElementById('users-table-body'),
    userFormError: document.getElementById('user-form-error'),
    
    // Main app elements
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
    checkAuthState();
});

// Check if user is authenticated
function checkAuthState() {
    if (state.token && state.user) {
        showMainApp();
    } else {
        showLoginPage();
    }
}

// Show login page
function showLoginPage() {
    elements.loginPage.classList.remove('hidden');
    elements.mainApp.classList.add('hidden');
    elements.loginUsername.focus();
}

// Show main application
function showMainApp() {
    elements.loginPage.classList.add('hidden');
    elements.mainApp.classList.remove('hidden');
    
    // Update user display
    elements.userDisplayName.textContent = state.user.username;
    
    // Show/hide admin link based on role
    if (state.user.role === 'admin') {
        elements.adminPanelLink.classList.remove('hidden');
    } else {
        elements.adminPanelLink.classList.add('hidden');
    }
    
    // Create session
    createSession();
}

// Event Listeners
function initializeEventListeners() {
    // Auth events
    elements.loginForm.addEventListener('submit', handleLogin);
    elements.userMenuBtn.addEventListener('click', toggleUserMenu);
    elements.changePasswordLink.addEventListener('click', showChangePasswordModal);
    elements.adminPanelLink.addEventListener('click', showAdminPanel);
    elements.logoutLink.addEventListener('click', handleLogout);
    elements.changePasswordForm.addEventListener('submit', handleChangePassword);
    elements.userForm.addEventListener('submit', handleUserFormSubmit);
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!elements.userMenuBtn.contains(e.target) && !elements.userDropdown.contains(e.target)) {
            elements.userDropdown.classList.add('hidden');
        }
    });

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

// ==================== Authentication ====================

async function handleLogin(e) {
    e.preventDefault();
    
    const username = elements.loginUsername.value.trim();
    const password = elements.loginPassword.value;
    
    elements.loginError.classList.add('hidden');
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Login failed');
        }
        
        // Store auth data
        state.token = data.token;
        state.user = data.user;
        localStorage.setItem('auth_token', data.token);
        localStorage.setItem('user_info', JSON.stringify(data.user));
        
        // Clear form
        elements.loginUsername.value = '';
        elements.loginPassword.value = '';
        
        showMainApp();
        showToast('Login successful!', 'success');
        
    } catch (error) {
        elements.loginError.textContent = error.message;
        elements.loginError.classList.remove('hidden');
    }
}

function handleLogout(e) {
    e.preventDefault();
    
    // Clear auth data
    state.token = null;
    state.user = null;
    state.sessionId = null;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_info');
    
    // Reset state
    state.purchaseFiles = [];
    state.saleFiles = [];
    state.purchaseItems = [];
    state.saleItems = [];
    state.matchedResults = null;
    state.summary = null;
    state.currentStep = 1;
    
    elements.userDropdown.classList.add('hidden');
    showLoginPage();
    showToast('Logged out successfully', 'info');
}

function toggleUserMenu() {
    elements.userDropdown.classList.toggle('hidden');
}

// API helper with auth
async function apiRequest(url, options = {}) {
    const headers = {
        ...options.headers
    };
    
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }
    
    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(options.body);
    }
    
    const response = await fetch(`${API_BASE_URL}${url}`, {
        ...options,
        headers
    });
    
    // Handle auth errors
    if (response.status === 401) {
        const data = await response.json();
        if (data.code === 'INVALID_TOKEN' || data.code === 'NO_TOKEN') {
            handleLogout({ preventDefault: () => {} });
            showToast('Session expired. Please login again.', 'warning');
            throw new Error('Session expired');
        }
    }
    
    return response;
}

// ==================== Change Password ====================

function showChangePasswordModal(e) {
    e.preventDefault();
    elements.userDropdown.classList.add('hidden');
    elements.changePasswordModal.classList.remove('hidden');
    elements.passwordError.classList.add('hidden');
    document.getElementById('current-password').value = '';
    document.getElementById('new-password').value = '';
    document.getElementById('confirm-password').value = '';
    document.getElementById('current-password').focus();
}

function closePasswordModal() {
    elements.changePasswordModal.classList.add('hidden');
}

async function handleChangePassword(e) {
    e.preventDefault();
    
    const currentPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    
    elements.passwordError.classList.add('hidden');
    
    if (newPassword !== confirmPassword) {
        elements.passwordError.textContent = 'New passwords do not match';
        elements.passwordError.classList.remove('hidden');
        return;
    }
    
    try {
        const response = await apiRequest('/auth/change-password', {
            method: 'POST',
            body: { current_password: currentPassword, new_password: newPassword }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to change password');
        }
        
        closePasswordModal();
        showToast('Password changed successfully!', 'success');
        
    } catch (error) {
        elements.passwordError.textContent = error.message;
        elements.passwordError.classList.remove('hidden');
    }
}

// ==================== Admin Panel ====================

function showAdminPanel(e) {
    e.preventDefault();
    elements.userDropdown.classList.add('hidden');
    elements.adminPanelModal.classList.remove('hidden');
    elements.userFormContainer.classList.add('hidden');
    loadUsers();
}

function closeAdminPanel() {
    elements.adminPanelModal.classList.add('hidden');
}

async function loadUsers() {
    elements.usersTableBody.innerHTML = '<tr><td colspan="6" class="loading-row">Loading users...</td></tr>';
    
    try {
        const response = await apiRequest('/admin/users');
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to load users');
        }
        
        renderUsersTable(data.users);
        
    } catch (error) {
        elements.usersTableBody.innerHTML = `<tr><td colspan="6" class="loading-row">Error: ${error.message}</td></tr>`;
    }
}

function renderUsersTable(users) {
    if (users.length === 0) {
        elements.usersTableBody.innerHTML = '<tr><td colspan="6" class="no-data-row">No users found</td></tr>';
        return;
    }
    
    elements.usersTableBody.innerHTML = users.map(user => `
        <tr>
            <td>${user.id}</td>
            <td>${user.username}</td>
            <td><span class="role-badge ${user.role}">${user.role}</span></td>
            <td>${formatDate(user.created_at)}</td>
            <td>${user.last_login ? formatDate(user.last_login) : 'Never'}</td>
            <td class="action-btns">
                <button class="btn btn-secondary btn-small" onclick="editUser(${user.id}, '${user.username}', '${user.role}')">Edit</button>
                ${user.id !== state.user.id ? `<button class="btn btn-danger btn-small" onclick="deleteUser(${user.id}, '${user.username}')">Delete</button>` : ''}
            </td>
        </tr>
    `).join('');
}

function showAddUserForm() {
    elements.userFormContainer.classList.remove('hidden');
    document.getElementById('edit-user-id').value = '';
    document.getElementById('user-username').value = '';
    document.getElementById('user-password').value = '';
    document.getElementById('user-password').required = true;
    document.getElementById('password-label').textContent = 'Password *';
    document.getElementById('user-role').value = 'user';
    document.getElementById('save-user-btn').textContent = 'Add User';
    elements.userFormError.classList.add('hidden');
    document.getElementById('user-username').focus();
}

function editUser(id, username, role) {
    elements.userFormContainer.classList.remove('hidden');
    document.getElementById('edit-user-id').value = id;
    document.getElementById('user-username').value = username;
    document.getElementById('user-password').value = '';
    document.getElementById('user-password').required = false;
    document.getElementById('password-label').textContent = 'Password (leave blank to keep current)';
    document.getElementById('user-role').value = role;
    document.getElementById('save-user-btn').textContent = 'Update User';
    elements.userFormError.classList.add('hidden');
    document.getElementById('user-username').focus();
}

function cancelUserForm() {
    elements.userFormContainer.classList.add('hidden');
    elements.userFormError.classList.add('hidden');
}

async function handleUserFormSubmit(e) {
    e.preventDefault();
    
    const userId = document.getElementById('edit-user-id').value;
    const username = document.getElementById('user-username').value.trim();
    const password = document.getElementById('user-password').value;
    const role = document.getElementById('user-role').value;
    
    elements.userFormError.classList.add('hidden');
    
    try {
        let response;
        
        if (userId) {
            // Update existing user
            const body = { username, role };
            if (password) body.password = password;
            
            response = await apiRequest(`/admin/users/${userId}`, {
                method: 'PUT',
                body
            });
        } else {
            // Create new user
            response = await apiRequest('/admin/users', {
                method: 'POST',
                body: { username, password, role }
            });
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Operation failed');
        }
        
        cancelUserForm();
        loadUsers();
        showToast(userId ? 'User updated successfully!' : 'User created successfully!', 'success');
        
    } catch (error) {
        elements.userFormError.textContent = error.message;
        elements.userFormError.classList.remove('hidden');
    }
}

async function deleteUser(id, username) {
    if (!confirm(`Are you sure you want to delete user "${username}"?`)) return;
    
    try {
        const response = await apiRequest(`/admin/users/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to delete user');
        }
        
        loadUsers();
        showToast('User deleted successfully!', 'success');
        
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// ==================== Session Management ====================

async function createSession() {
    try {
        const response = await apiRequest('/session/create', {
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
        if (error.message !== 'Session expired') {
            showToast('Failed to create session. Is the server running?', 'error');
            console.error('Session creation error:', error);
        }
    }
}

async function startNewSession() {
    // Reset state
    state.purchaseFiles = [];
    state.saleFiles = [];
    state.purchaseItems = [];
    state.saleItems = [];
    state.matchedResults = null;
    state.summary = null;
    state.currentStep = 1;

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

// ==================== File Handling ====================

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

// ==================== Drag and Drop ====================

function setupDragAndDrop(elementId, type) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
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

// ==================== Bill Processing ====================

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
        if (error.message !== 'Session expired') {
            showToast(`Error processing bills: ${error.message}`, 'error');
            console.error('Processing error:', error);
        }
    }
}

async function uploadFile(file, type) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', state.sessionId);

    const response = await fetch(`${API_BASE_URL}/upload/${type}`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${state.token}`
        },
        body: formData
    });

    if (response.status === 401) {
        handleLogout({ preventDefault: () => {} });
        showToast('Session expired. Please login again.', 'warning');
        throw new Error('Session expired');
    }

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Upload failed');
    }

    const data = await response.json();
    return data;
}

async function fetchSessionData() {
    const response = await apiRequest(`/session/${state.sessionId}`);
    const data = await response.json();

    state.purchaseItems = data.purchase_items || [];
    state.saleItems = data.sale_items || [];

    renderItems();
}

// ==================== Item Rendering ====================

function renderItems() {
    renderItemsList(state.purchaseItems, 'purchase-items', 'purchase');
    renderItemsList(state.saleItems, 'sale-items', 'sale');
    
    document.getElementById('purchase-count').textContent = state.purchaseItems.length;
    document.getElementById('sale-count').textContent = state.saleItems.length;
}

function renderItemsList(items, containerId, type) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
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

// ==================== Item CRUD Operations ====================

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
        const response = await apiRequest('/items/add', {
            method: 'POST',
            body: {
                session_id: state.sessionId,
                item_type: type,
                item: item
            }
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
        if (error.message !== 'Session expired') {
            showToast(`Error adding item: ${error.message}`, 'error');
        }
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
        const response = await apiRequest('/items/update', {
            method: 'POST',
            body: {
                session_id: state.sessionId,
                item_type: type,
                item_index: index,
                updates: updates
            }
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
        if (error.message !== 'Session expired') {
            showToast(`Error updating item: ${error.message}`, 'error');
        }
    }
}

async function deleteItem(type, index) {
    if (!confirm('Are you sure you want to delete this item?')) return;

    try {
        const response = await apiRequest('/items/delete', {
            method: 'POST',
            body: {
                session_id: state.sessionId,
                item_type: type,
                item_index: index
            }
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
        if (error.message !== 'Session expired') {
            showToast(`Error deleting item: ${error.message}`, 'error');
        }
    }
}

function closeModal() {
    elements.addItemModal.classList.add('hidden');
    elements.addItemForm.onsubmit = handleAddItem;
}

// ==================== Item Matching ====================

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
        const response = await apiRequest('/match', {
            method: 'POST',
            body: { session_id: state.sessionId }
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
        if (error.message !== 'Session expired') {
            showToast(`Error matching items: ${error.message}`, 'error');
            console.error('Matching error:', error);
        }
    }
}

// ==================== Results Rendering ====================

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

// ==================== Tab Switching ====================

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// ==================== Export ====================

async function exportResults() {
    if (!state.sessionId || !state.matchedResults) {
        showToast('No results to export', 'warning');
        return;
    }

    showLoading('Generating Excel file...');

    try {
        const response = await fetch(`${API_BASE_URL}/export/${state.sessionId}`, {
            headers: {
                'Authorization': `Bearer ${state.token}`
            }
        });
        
        if (response.status === 401) {
            handleLogout({ preventDefault: () => {} });
            showToast('Session expired. Please login again.', 'warning');
            throw new Error('Session expired');
        }
        
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
        if (error.message !== 'Session expired') {
            showToast(`Error exporting: ${error.message}`, 'error');
            console.error('Export error:', error);
        }
    }
}

// ==================== Step Navigation ====================

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

// ==================== Loading ====================

function showLoading(message = 'Processing...') {
    elements.loadingMessage.textContent = message;
    elements.loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    elements.loadingOverlay.classList.add('hidden');
}

// ==================== Toast Notifications ====================

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

// ==================== Utility Functions ====================

function formatNumber(num) {
    return new Intl.NumberFormat('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(num);
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-IN', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return dateStr;
    }
}

// ==================== Password Toggle ====================

function togglePassword(inputId, button) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
        button.textContent = '🙈';
        button.title = 'Hide password';
    } else {
        input.type = 'password';
        button.textContent = '👁️';
        button.title = 'Show password';
    }
}

// Make functions available globally
window.togglePassword = togglePassword;
window.removeFile = removeFile;
window.addItem = addItem;
window.editItem = editItem;
window.deleteItem = deleteItem;
window.closeModal = closeModal;
window.goToStep = goToStep;
window.startNewSession = startNewSession;
window.closePasswordModal = closePasswordModal;
window.closeAdminPanel = closeAdminPanel;
window.showAddUserForm = showAddUserForm;
window.editUser = editUser;
window.cancelUserForm = cancelUserForm;
window.deleteUser = deleteUser;
