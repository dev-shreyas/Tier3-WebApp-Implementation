from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
import tempfile
from datetime import datetime, timedelta
from functools import wraps
import hashlib

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'prod-secret-key-change-this-in-production')

# Use a writable location for the database
DB_PATH = os.path.join(tempfile.gettempdir(), "task_manager.db")

def get_db():
    db = sqlite3.connect(DB_PATH, timeout=10.0, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    return db

def init_db():
    """Initialize the database with the required schema"""
    try:
        db = get_db()
        
        # Users table
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Categories table
        db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color TEXT DEFAULT '#6366f1',
                icon TEXT DEFAULT 'inbox',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Tasks table with enhanced schema
        db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                due_date DATE,
                tags TEXT,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            )
        """)
        
        # Activity log table
        db.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                task_id INTEGER,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES items(id) ON DELETE SET NULL
            )
        """)
        
        db.commit()
        
        # Create default user and categories if needed
        try:
            cursor = db.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                      ('demo', 'demo@taskmanager.local', hashlib.sha256('demo'.encode()).hexdigest()))
            user_id = cursor.lastrowid
            
            default_categories = [
                ('Work', '#3b82f6', 'briefcase'),
                ('Personal', '#8b5cf6', 'user'),
                ('Shopping', '#ec4899', 'bag'),
                ('Health', '#10b981', 'heart'),
            ]
            
            for name, color, icon in default_categories:
                db.execute("INSERT INTO categories (user_id, name, color, icon) VALUES (?, ?, ?, ?)",
                          (user_id, name, color, icon))
            
            db.commit()
        except sqlite3.IntegrityError:
            pass
        
        db.close()
    except Exception as e:
        app.logger.error(f"Database initialization error: {str(e)}")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def log_activity(user_id, action, task_id=None, details=None):
    """Log user activity for analytics with retry logic"""
    import time
    max_retries = 3
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        db = None
        try:
            db = get_db()
            db.execute(
                "INSERT INTO activity_log (user_id, action, task_id, details) VALUES (?, ?, ?, ?)",
                (user_id, action, task_id, details)
            )
            db.commit()
            return
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e) and attempt < max_retries - 1:
                app.logger.debug(f"Database locked, retrying ({attempt + 1}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                app.logger.error(f"Error logging activity (attempt {attempt + 1}/{max_retries}): {str(e)}")
        except Exception as e:
            app.logger.error(f"Error logging activity: {str(e)}")
        finally:
            if db:
                db.close()

# Authentication Routes
@app.route("/auth/login", methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('login'))
        
        db = None
        try:
            db = get_db()
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            user = db.execute(
                "SELECT * FROM users WHERE username = ? AND password = ?",
                (username, hashed_password)
            ).fetchone()
            
            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash(f'Welcome back, {username}!', 'success')
                
                # Log activity after successful login
                try:
                    log_activity(user['id'], 'login')
                except Exception as log_error:
                    app.logger.warning(f"Could not log login activity: {str(log_error)}")
                
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'error')
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e):
                app.logger.error(f"Database locked during login: {str(e)}")
                flash('Database is busy. Please try again in a moment.', 'error')
            else:
                app.logger.error(f"Database error during login: {str(e)}")
                flash('A database error occurred. Please try again.', 'error')
        except Exception as e:
            app.logger.error(f"Login error: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
        finally:
            if db:
                db.close()
    
    return render_template("auth/login.html")

@app.route("/auth/register", methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([username, email, password, confirm_password]):
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return redirect(url_for('register'))
        
        db = None
        try:
            db = get_db()
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            # Insert user
            cursor = db.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, hashed_password)
            )
            user_id = cursor.lastrowid
            
            # Create default categories for new user
            default_categories = [
                ('Work', '#3b82f6', 'briefcase'),
                ('Personal', '#8b5cf6', 'user'),
                ('Shopping', '#ec4899', 'bag'),
                ('Health', '#10b981', 'heart'),
            ]
            
            for name, color, icon in default_categories:
                db.execute("INSERT INTO categories (user_id, name, color, icon) VALUES (?, ?, ?, ?)",
                          (user_id, name, color, icon))
            
            # Commit all changes at once
            db.commit()
            
            # Set session
            session['user_id'] = user_id
            session['username'] = username
            
            flash('Registration successful! Welcome!', 'success')
            
            # Log activity after successful registration
            try:
                log_activity(user_id, 'register')
            except Exception as log_error:
                app.logger.warning(f"Could not log registration activity: {str(log_error)}")
            
            return redirect(url_for('dashboard'))
            
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e):
                app.logger.error(f"Database locked during registration: {str(e)}")
                flash('Database is busy. Please try again in a moment.', 'error')
            else:
                app.logger.error(f"Database error during registration: {str(e)}")
                flash('A database error occurred. Please try again.', 'error')
            return redirect(url_for('register'))
        except sqlite3.IntegrityError as e:
            app.logger.error(f"Integrity error during registration: {str(e)}")
            flash('Username or email already exists.', 'error')
            return redirect(url_for('register'))
        except Exception as e:
            app.logger.error(f"Registration error: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
            return redirect(url_for('register'))
        finally:
            if db:
                db.close()
    
    return render_template("auth/register.html")

@app.route("/auth/logout")
def logout():
    """User logout"""
    if 'user_id' in session:
        user_id = session['user_id']
        log_activity(user_id, 'logout')
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# Main Dashboard Route
@app.route("/")
@login_required
def dashboard():
    """Main dashboard with task overview"""
    try:
        user_id = session['user_id']
        db = get_db()
        
        # Get all tasks for user
        items = db.execute(
            """SELECT i.*, c.name as category_name, c.color as category_color 
               FROM items i 
               LEFT JOIN categories c ON i.category_id = c.id 
               WHERE i.user_id = ? 
               ORDER BY i.due_date ASC, i.priority DESC, i.created_at DESC""",
            (user_id,)
        ).fetchall()
        
        # Get categories
        categories = db.execute(
            "SELECT * FROM categories WHERE user_id = ? ORDER BY name",
            (user_id,)
        ).fetchall()
        
        # Calculate statistics
        total = len(items)
        completed = sum(1 for item in items if item['status'] == 'completed')
        pending = sum(1 for item in items if item['status'] == 'pending')
        
        # Get overdue tasks
        today = datetime.now().date()
        overdue = sum(1 for item in items 
                     if item['due_date'] and item['status'] != 'completed' 
                     and datetime.strptime(item['due_date'], '%Y-%m-%d').date() < today)
        
        # Priority breakdown
        priority_stats = {
            'high': sum(1 for item in items if item['priority'] == 'high' and item['status'] != 'completed'),
            'medium': sum(1 for item in items if item['priority'] == 'medium' and item['status'] != 'completed'),
            'low': sum(1 for item in items if item['priority'] == 'low' and item['status'] != 'completed'),
        }
        
        db.close()
        
        return render_template(
            "dashboard.html",
            items=items,
            categories=categories,
            total=total,
            completed=completed,
            pending=pending,
            overdue=overdue,
            priority_stats=priority_stats
        )
    except Exception as e:
        app.logger.error(f"Dashboard error: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return render_template("dashboard.html", items=[], categories=[], total=0, completed=0, pending=0, overdue=0)

@app.route("/add", methods=['GET', 'POST'])
@login_required
def add_item():
    """Add a new task"""
    user_id = session['user_id']
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            category_id = request.form.get('category_id')
            priority = request.form.get('priority', 'medium')
            due_date = request.form.get('due_date')
            tags = request.form.get('tags')
            
            if not name:
                flash('Task name is required!', 'error')
                return redirect(url_for('add_item'))
            
            db = get_db()
            db.execute(
                """INSERT INTO items (user_id, category_id, name, description, priority, due_date, tags, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, category_id if category_id else None, name, description, priority, due_date, tags, 'pending')
            )
            db.commit()
            db.close()
            
            log_activity(user_id, 'task_created', details=name)
            flash('Task created successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            app.logger.error(f"Error adding task: {str(e)}")
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('add_item'))
    
    try:
        db = get_db()
        categories = db.execute(
            "SELECT * FROM categories WHERE user_id = ? ORDER BY name",
            (user_id,)
        ).fetchall()
        db.close()
    except Exception as e:
        categories = []
        app.logger.error(f"Error fetching categories: {str(e)}")
    
    return render_template("add_item.html", categories=categories)

@app.route("/edit/<int:item_id>", methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    """Edit an existing task"""
    user_id = session['user_id']
    
    try:
        db = get_db()
        item = db.execute(
            "SELECT * FROM items WHERE id = ? AND user_id = ?",
            (item_id, user_id)
        ).fetchone()
        
        if not item:
            flash('Task not found!', 'error')
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            category_id = request.form.get('category_id')
            priority = request.form.get('priority')
            status = request.form.get('status')
            due_date = request.form.get('due_date')
            tags = request.form.get('tags')
            
            if not name:
                flash('Task name is required!', 'error')
                return redirect(url_for('edit_item', item_id=item_id))
            
            completed_at = None
            if status == 'completed' and item['status'] != 'completed':
                completed_at = datetime.now()
            
            db.execute(
                """UPDATE items 
                   SET name = ?, description = ?, category_id = ?, priority = ?, status = ?, due_date = ?, tags = ?, completed_at = ?, updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (name, description, category_id if category_id else None, priority, status, due_date, tags, completed_at, item_id)
            )
            db.commit()
            db.close()
            
            log_activity(user_id, 'task_updated', item_id, name)
            flash('Task updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        
        categories = db.execute(
            "SELECT * FROM categories WHERE user_id = ? ORDER BY name",
            (user_id,)
        ).fetchall()
        db.close()
        
        return render_template("edit_item.html", item=item, categories=categories)
    except Exception as e:
        app.logger.error(f"Error editing task: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route("/delete/<int:item_id>", methods=['POST'])
@login_required
def delete_item(item_id):
    """Delete a task"""
    user_id = session['user_id']
    
    try:
        db = get_db()
        item = db.execute(
            "SELECT name FROM items WHERE id = ? AND user_id = ?",
            (item_id, user_id)
        ).fetchone()
        
        if item:
            db.execute("DELETE FROM items WHERE id = ?", (item_id,))
            db.commit()
            log_activity(user_id, 'task_deleted', item_id, item['name'])
            flash('Task deleted successfully!', 'success')
        else:
            flash('Task not found!', 'error')
        
        db.close()
    except Exception as e:
        app.logger.error(f"Error deleting task: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

# Category Management
@app.route("/categories", methods=['GET', 'POST'])
@login_required
def manage_categories():
    """Manage task categories"""
    user_id = session['user_id']
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            color = request.form.get('color', '#6366f1')
            icon = request.form.get('icon', 'inbox')
            
            if not name:
                flash('Category name is required!', 'error')
                return redirect(url_for('manage_categories'))
            
            db = get_db()
            db.execute(
                "INSERT INTO categories (user_id, name, color, icon) VALUES (?, ?, ?, ?)",
                (user_id, name, color, icon)
            )
            db.commit()
            db.close()
            
            log_activity(user_id, 'category_created', details=name)
            flash('Category created successfully!', 'success')
            return redirect(url_for('manage_categories'))
        except Exception as e:
            app.logger.error(f"Error creating category: {str(e)}")
            flash(f'Error: {str(e)}', 'error')
    
    try:
        db = get_db()
        categories = db.execute(
            "SELECT * FROM categories WHERE user_id = ? ORDER BY name",
            (user_id,)
        ).fetchall()
        db.close()
    except Exception as e:
        categories = []
        app.logger.error(f"Error fetching categories: {str(e)}")
    
    return render_template("categories.html", categories=categories)

@app.route("/categories/<int:category_id>/delete", methods=['POST'])
@login_required
def delete_category(category_id):
    """Delete a category"""
    user_id = session['user_id']
    
    try:
        db = get_db()
        category = db.execute(
            "SELECT name FROM categories WHERE id = ? AND user_id = ?",
            (category_id, user_id)
        ).fetchone()
        
        if category:
            db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            db.commit()
            log_activity(user_id, 'category_deleted', details=category['name'])
            flash('Category deleted successfully!', 'success')
        else:
            flash('Category not found!', 'error')
        
        db.close()
    except Exception as e:
        app.logger.error(f"Error deleting category: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('manage_categories'))

# Search and Filter
@app.route("/search")
@login_required
def search():
    """Search tasks"""
    user_id = session['user_id']
    query = request.args.get('q', '')
    
    try:
        db = get_db()
        if query:
            items = db.execute(
                """SELECT i.*, c.name as category_name, c.color as category_color 
                   FROM items i 
                   LEFT JOIN categories c ON i.category_id = c.id 
                   WHERE i.user_id = ? AND (i.name LIKE ? OR i.description LIKE ? OR i.tags LIKE ?)
                   ORDER BY i.created_at DESC""",
                (user_id, f'%{query}%', f'%{query}%', f'%{query}%')
            ).fetchall()
        else:
            items = []
        
        categories = db.execute(
            "SELECT * FROM categories WHERE user_id = ? ORDER BY name",
            (user_id,)
        ).fetchall()
        
        db.close()
    except Exception as e:
        items = []
        categories = []
        app.logger.error(f"Search error: {str(e)}")
    
    return render_template("search.html", items=items, query=query, categories=categories)

# Analytics and Statistics
@app.route("/analytics")
@login_required
def analytics():
    """User analytics dashboard"""
    user_id = session['user_id']
    
    try:
        db = get_db()
        
        # Get all tasks
        items = db.execute(
            "SELECT * FROM items WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        
        # Get activity log
        activity = db.execute(
            "SELECT * FROM activity_log WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
            (user_id,)
        ).fetchall()
        
        db.close()
        
        # Calculate statistics
        total = len(items)
        completed = sum(1 for item in items if item['status'] == 'completed')
        pending = sum(1 for item in items if item['status'] == 'pending')
        completion_rate = round((completed / total * 100) if total > 0 else 0, 1)
        
        # Priority breakdown
        priority_stats = {
            'high': sum(1 for item in items if item['priority'] == 'high'),
            'medium': sum(1 for item in items if item['priority'] == 'medium'),
            'low': sum(1 for item in items if item['priority'] == 'low'),
        }
        
        # Due date statistics
        today = datetime.now().date()
        due_today = sum(1 for item in items 
                       if item['due_date'] and item['status'] != 'completed'
                       and datetime.strptime(item['due_date'], '%Y-%m-%d').date() == today)
        
        overdue = sum(1 for item in items 
                     if item['due_date'] and item['status'] != 'completed'
                     and datetime.strptime(item['due_date'], '%Y-%m-%d').date() < today)
        
        return render_template(
            "analytics.html",
            total=total,
            completed=completed,
            pending=pending,
            completion_rate=completion_rate,
            priority_stats=priority_stats,
            due_today=due_today,
            overdue=overdue,
            activity=activity,
            items=items
        )
    except Exception as e:
        app.logger.error(f"Analytics error: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return render_template("analytics.html", total=0, completed=0, pending=0, completion_rate=0, priority_stats={}, due_today=0, overdue=0, activity=[], items=[])

# API Endpoints
@app.route("/api/data")
@login_required
def data():
    """API endpoint to get all tasks as JSON"""
    try:
        user_id = session['user_id']
        db = get_db()
        rows = db.execute(
            "SELECT * FROM items WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        db.close()
        return jsonify([dict(row) for row in rows])
    except Exception as e:
        app.logger.error(f"API error: {str(e)}")
        return jsonify(error=str(e)), 500

@app.route("/api/stats")
@login_required
def stats():
    """Get statistics about tasks"""
    try:
        user_id = session['user_id']
        db = get_db()
        
        total = db.execute("SELECT COUNT(*) as count FROM items WHERE user_id = ?", (user_id,)).fetchone()['count']
        completed = db.execute("SELECT COUNT(*) as count FROM items WHERE user_id = ? AND status = 'completed'", (user_id,)).fetchone()['count']
        pending = db.execute("SELECT COUNT(*) as count FROM items WHERE user_id = ? AND status = 'pending'", (user_id,)).fetchone()['count']
        
        db.close()
        
        return jsonify({
            'total': total,
            'completed': completed,
            'pending': pending,
            'completion_rate': round((completed / total * 100) if total > 0 else 0, 1)
        })
    except Exception as e:
        app.logger.error(f"Stats error: {str(e)}")
        return jsonify(error=str(e)), 500

@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify(status="ok", timestamp=datetime.now().isoformat())

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=7003, debug=False)