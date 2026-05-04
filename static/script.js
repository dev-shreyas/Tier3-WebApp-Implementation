// Dark mode management
const darkModeToggle = {
    init() {
        this.loadPreference();
        this.setupToggleButton();
    },
    
    loadPreference() {
        const savedMode = localStorage.getItem('darkMode');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const isDarkMode = savedMode ? JSON.parse(savedMode) : prefersDark;
        
        if (isDarkMode) {
            this.enable();
        }
    },
    
    setupToggleButton() {
        const toggle = document.querySelector('.dark-mode-toggle');
        if (toggle) {
            toggle.addEventListener('click', () => {
                const isDarkMode = document.documentElement.classList.contains('dark-mode');
                isDarkMode ? this.disable() : this.enable();
            });
        }
    },
    
    enable() {
        document.documentElement.classList.add('dark-mode');
        localStorage.setItem('darkMode', 'true');
        this.updateToggleIcon();
    },
    
    disable() {
        document.documentElement.classList.remove('dark-mode');
        localStorage.setItem('darkMode', 'false');
        this.updateToggleIcon();
    },
    
    updateToggleIcon() {
        const toggle = document.querySelector('.dark-mode-toggle');
        if (toggle) {
            const icon = toggle.querySelector('i');
            const isDarkMode = document.documentElement.classList.contains('dark-mode');
            if (icon) {
                icon.className = isDarkMode ? 'bi bi-brightness-high' : 'bi bi-moon';
            }
        }
    }
};

// Auto-hide alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    // Initialize dark mode
    darkModeToggle.init();
    
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Initialize task checkboxes
    initializeTaskCheckboxes();
    
    // Initialize filter buttons
    initializeFilters();
});

// Update statistics dynamically
async function updateStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        const totalElement = document.getElementById('total-count');
        const pendingElement = document.getElementById('pending-count');
        const completedElement = document.getElementById('completed-count');
        
        if (totalElement) totalElement.textContent = data.total;
        if (pendingElement) pendingElement.textContent = data.pending;
        if (completedElement) completedElement.textContent = data.completed;
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

// Refresh stats every 30 seconds
setInterval(updateStats, 30000);

// Task checkbox functionality
function initializeTaskCheckboxes() {
    const checkboxes = document.querySelectorAll('.task-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const taskId = this.getAttribute('data-task-id');
            const taskItem = this.closest('.task-item');
            
            if (this.checked) {
                // Mark as completed
                const status = 'completed';
                updateTaskStatus(taskId, status, taskItem);
            } else {
                // Mark as pending
                const status = 'pending';
                updateTaskStatus(taskId, status, taskItem);
            }
        });
    });
}

async function updateTaskStatus(taskId, status, taskItem) {
    try {
        const formData = new FormData();
        formData.append('status', status);
        
        const response = await fetch(`/edit/${taskId}`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            // Update task item appearance
            if (status === 'completed') {
                taskItem.classList.add('completed');
                taskItem.setAttribute('data-status', 'completed');
            } else {
                taskItem.classList.remove('completed');
                taskItem.setAttribute('data-status', 'pending');
            }
            updateStats();
        }
    } catch (error) {
        console.error('Error updating task:', error);
    }
}

// Filter functionality
function initializeFilters() {
    const filterRadios = document.querySelectorAll('input[name="filter"]');
    filterRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            filterTasks(this.value);
        });
    });
}

function filterTasks(filter) {
    const taskItems = document.querySelectorAll('.task-item');
    taskItems.forEach(item => {
        const status = item.getAttribute('data-status');
        
        if (filter === 'all') {
            item.style.display = 'block';
        } else if (filter === status) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

// Smooth scroll for navigation
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add animation to task items on page load
window.addEventListener('load', function() {
    const taskItems = document.querySelectorAll('.task-item');
    taskItems.forEach((item, index) => {
        item.style.animation = `fadeInUp 0.3s ease ${index * 50}ms forwards`;
        item.style.opacity = '0';
    });
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .stat-card {
        animation: slideDown 0.5s ease forwards;
    }
    
    .card {
        animation: fadeInUp 0.5s ease forwards;
    }
`;
document.head.appendChild(style);

// Form validation
document.querySelectorAll('.task-form').forEach(form => {
    form.addEventListener('submit', function(e) {
        const nameInput = this.querySelector('#name');
        if (!nameInput || !nameInput.value.trim()) {
            e.preventDefault();
            if (nameInput) {
                nameInput.focus();
                nameInput.classList.add('is-invalid');
                
                setTimeout(() => {
                    nameInput.classList.remove('is-invalid');
                }, 2000);
            }
        }
    });
});

// Search input debouncing
let searchTimeout;
const searchInput = document.getElementById('searchInput');
if (searchInput) {
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value;
        
        if (query.length > 2) {
            // You can add real-time search preview here
            console.log('Search query:', query);
        }
    });
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Escape to close modals
    if (e.key === 'Escape') {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        });
    }
});

// Add task counter badge
function updateTaskCount() {
    const taskList = document.querySelectorAll('.task-item');
    const count = taskList.length;
    
    if (count === 0) {
        console.log('No tasks found');
    }
    
    return count;
}

// Real-time clock on dashboard
function updateDateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    const dateString = now.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
    
    // Update if time display element exists
    const timeDisplay = document.getElementById('current-time');
    if (timeDisplay) {
        timeDisplay.textContent = timeString;
    }
}

setInterval(updateDateTime, 1000);

// Copy to clipboard functionality
document.querySelectorAll('[data-copy]').forEach(element => {
    element.addEventListener('click', function() {
        const text = this.getAttribute('data-copy');
        navigator.clipboard.writeText(text).then(() => {
            // Show toast notification
            const originalText = this.textContent;
            this.textContent = 'Copied!';
            setTimeout(() => {
                this.textContent = originalText;
            }, 2000);
        });
    });
});

// Tooltips
document.addEventListener('DOMContentLoaded', function() {
    const tooltipElements = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipElements.forEach(element => {
        new bootstrap.Tooltip(element);
    });
});

// Performance monitoring
window.addEventListener('load', function() {
    const perfData = window.performance.timing;
    const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
    console.log('Page load time:', pageLoadTime, 'ms');
});
