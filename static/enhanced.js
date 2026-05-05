/**
 * Enhanced Task Manager - Advanced Features
 * Features: Dark Mode, Notifications, Advanced Filters, Task Analytics
 */

class TaskManager {
    constructor() {
        this.tasks = [];
        this.filters = {
            search: '',
            priority: '',
            category: '',
            status: '',
            sortBy: 'due_date'
        };
        this.initializeApp();
    }

    initializeApp() {
        this.setupDarkMode();
        this.setupNotifications();
        this.setupFilters();
        this.setupKeyboardShortcuts();
        this.setupTaskActions();
        this.loadTasks();
    }

    // Dark Mode Toggle
    setupDarkMode() {
        const darkModeToggle = document.getElementById('darkModeToggle');
        const htmlElement = document.documentElement;
        
        // Check for saved preference or system preference
        const isDarkMode = localStorage.getItem('darkMode') === 'true' ||
                          (!localStorage.getItem('darkMode') && 
                           window.matchMedia('(prefers-color-scheme: dark)').matches);
        
        if (isDarkMode) {
            htmlElement.classList.add('dark-mode');
            if (darkModeToggle) darkModeToggle.checked = true;
        }

        if (darkModeToggle) {
            darkModeToggle.addEventListener('change', (e) => {
                htmlElement.classList.toggle('dark-mode');
                localStorage.setItem('darkMode', htmlElement.classList.contains('dark-mode'));
            });
        }
    }

    // Notification System
    setupNotifications() {
        this.showNotification = (message, type = 'info', duration = 3000) => {
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.innerHTML = `
                <div class="notification-content">
                    ${this.getNotificationIcon(type)} ${message}
                </div>
                <button class="notification-close" onclick="this.parentElement.remove()">✕</button>
            `;
            
            document.body.appendChild(notification);
            
            if (duration) {
                setTimeout(() => notification.remove(), duration);
            }
        };
    }

    getNotificationIcon(type) {
        const icons = {
            'success': '✓',
            'error': '✕',
            'info': 'ℹ',
            'warning': '⚠'
        };
        return icons[type] || '●';
    }

    // Advanced Filtering
    setupFilters() {
        const filterInputs = document.querySelectorAll('[data-filter]');
        filterInputs.forEach(input => {
            input.addEventListener('change', (e) => {
                const filterName = e.target.getAttribute('data-filter');
                this.filters[filterName] = e.target.value;
                this.applyFilters();
            });
        });
    }

    applyFilters() {
        const taskItems = document.querySelectorAll('.task-item');
        let visibleCount = 0;

        taskItems.forEach(item => {
            let matches = true;

            // Search filter
            if (this.filters.search) {
                const title = item.querySelector('.task-title')?.textContent.toLowerCase() || '';
                matches = matches && title.includes(this.filters.search.toLowerCase());
            }

            // Priority filter
            if (this.filters.priority) {
                const priority = item.getAttribute('data-priority');
                matches = matches && priority === this.filters.priority;
            }

            // Status filter
            if (this.filters.status) {
                const status = item.getAttribute('data-status');
                matches = matches && status === this.filters.status;
            }

            // Category filter
            if (this.filters.category) {
                const category = item.getAttribute('data-category');
                matches = matches && category === this.filters.category;
            }

            item.style.display = matches ? 'flex' : 'none';
            if (matches) visibleCount++;
        });

        this.updateFilterResults(visibleCount);
    }

    updateFilterResults(count) {
        const resultElement = document.getElementById('filterResults');
        if (resultElement) {
            resultElement.textContent = `${count} task${count !== 1 ? 's' : ''}`;
        }
    }

    // Keyboard Shortcuts
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+N or Cmd+N: New Task
            if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                e.preventDefault();
                window.location.href = '/add';
            }

            // Ctrl+F or Cmd+F: Focus Search
            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                e.preventDefault();
                document.getElementById('taskSearch')?.focus();
            }

            // Esc: Clear Search
            if (e.key === 'Escape') {
                const search = document.getElementById('taskSearch');
                if (search) {
                    search.value = '';
                    search.dispatchEvent(new Event('input'));
                }
            }
        });
    }

    // Task Actions
    setupTaskActions() {
        // Mark task as complete
        document.querySelectorAll('.task-toggle').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const taskId = e.target.getAttribute('data-task-id');
                const taskItem = e.target.closest('.task-item');
                
                if (e.target.checked) {
                    taskItem.classList.add('completed');
                    this.showNotification('Task completed! 🎉', 'success');
                } else {
                    taskItem.classList.remove('completed');
                    this.showNotification('Task marked as pending', 'info');
                }
            });
        });

        // Bulk actions
        const selectAllCheckbox = document.getElementById('selectAllTasks');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => {
                document.querySelectorAll('.task-toggle').forEach(checkbox => {
                    checkbox.checked = e.target.checked;
                    checkbox.dispatchEvent(new Event('change'));
                });
            });
        }
    }

    loadTasks() {
        const taskItems = document.querySelectorAll('.task-item');
        this.tasks = Array.from(taskItems).map(item => ({
            id: item.getAttribute('data-task-id'),
            title: item.querySelector('.task-title')?.textContent,
            priority: item.getAttribute('data-priority'),
            status: item.getAttribute('data-status'),
            dueDate: item.getAttribute('data-due-date')
        }));
    }

    // Analytics Functions
    getTaskStats() {
        const total = this.tasks.length;
        const completed = this.tasks.filter(t => t.status === 'completed').length;
        const overdue = this.tasks.filter(t => {
            if (t.status === 'completed' || !t.dueDate) return false;
            return new Date(t.dueDate) < new Date();
        }).length;

        return { total, completed, overdue };
    }

    // Export functions
    exportAsPDF() {
        if (typeof jspdf === 'undefined') {
            this.showNotification('PDF export not available', 'error');
            return;
        }
        this.showNotification('Exporting as PDF...', 'info', 1000);
    }

    exportAsCSV() {
        const rows = [['Task', 'Priority', 'Status', 'Due Date']];
        
        this.tasks.forEach(task => {
            rows.push([task.title, task.priority, task.status, task.dueDate || 'N/A']);
        });

        let csvContent = 'data:text/csv;charset=utf-8,' + 
            rows.map(r => r.map(cell => `"${cell}"`).join(',')).join('\n');

        const link = document.createElement('a');
        link.setAttribute('href', encodeURI(csvContent));
        link.setAttribute('download', `tasks-${new Date().toISOString().split('T')[0]}.csv`);
        link.click();

        this.showNotification('Tasks exported as CSV! 📥', 'success');
    }

    // Timer/Pomodoro
    startPomodoroTimer(minutes = 25) {
        let timeLeft = minutes * 60;
        const startTime = Date.now();
        
        const timer = setInterval(() => {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            timeLeft = minutes * 60 - elapsed;

            if (timeLeft <= 0) {
                clearInterval(timer);
                this.showNotification('Pomodoro timer finished! 🍅', 'success');
            }
        }, 1000);

        return { timer, timeLeft };
    }
}

// Initialize Task Manager
const taskManager = new TaskManager();

// Utility Functions
function getColorByPriority(priority) {
    const colors = {
        'high': '#ef4444',
        'medium': '#f59e0b',
        'low': '#10b981'
    };
    return colors[priority] || '#6366f1';
}

function formatDate(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

function getDaysUntilDue(dueDate) {
    const today = new Date();
    const due = new Date(dueDate);
    const days = Math.ceil((due - today) / (1000 * 60 * 60 * 24));
    
    if (days < 0) return `${Math.abs(days)} days overdue`;
    if (days === 0) return 'Due today';
    if (days === 1) return 'Due tomorrow';
    return `Due in ${days} days`;
}

// Export for use in templates
window.TaskManager = TaskManager;
window.getColorByPriority = getColorByPriority;
window.formatDate = formatDate;
window.getDaysUntilDue = getDaysUntilDue;
