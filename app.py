import os
import sqlite3
import re
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv  

# Tambahkan import resmi untuk SDK SendGrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import requests

# Muat variabel dari file .env
load_dotenv()

app = Flask(__name__)
DB_NAME = "resume.db"

# 1. SETUP PATH DIREKTORI INSTANCE
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')

# 2. CONFIG URI & BINDS
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(INSTANCE_DIR, 'database.db')}"

app.config['SQLALCHEMY_BINDS'] = {
    'admin_db': f"sqlite:///{os.path.join(INSTANCE_DIR, 'admin.db')}",
    'contact_db': f"sqlite:///{os.path.join(INSTANCE_DIR, 'contact.db')}",
    'showcase_db': f"sqlite:///{os.path.join(INSTANCE_DIR, 'showcase.db')}"
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 3. INISIASI ELEMEN DB
db = SQLAlchemy(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-fallback-key-12345')

# Regex validasi email
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

def jakarta_now():
    return datetime.now(ZoneInfo("Asia/Jakarta")).replace(tzinfo=None)
    
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static/uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    
# =========================================================================
# DATABASE UTAMA (database.db)
# =========================================================================
class ProfileSection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bio_id = db.Column(db.Text, nullable=False)
    bio_en = db.Column(db.Text, nullable=False)

class Experience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title_id = db.Column(db.String(100), nullable=False)
    title_en = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    description_id = db.Column(db.Text, nullable=False)
    description_en = db.Column(db.Text, nullable=False)
    tech_stack = db.Column(db.String(200), nullable=False)

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=True)
    name_id = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100), nullable=False)
    level_id = db.Column(db.String(50), nullable=False)
    level_en = db.Column(db.String(50), nullable=False)

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    text_id = db.Column(db.String(200), nullable=False)
    text_en = db.Column(db.String(200), nullable=False)
    subtext_id = db.Column(db.String(200), nullable=False)
    subtext_en = db.Column(db.String(200), nullable=False)
    
# =========================================================================
# DATABASE TERPISAH (admin.db & contact.db)
# =========================================================================
class AdminUser(UserMixin, db.Model):
    __bind_key__ = 'admin_db'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

class ContactMessage(db.Model):
    __bind_key__ = 'contact_db'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    
class PageView(db.Model):
    __bind_key__ = 'admin_db'
    id = db.Column(db.Integer, primary_key=True)
    page_url = db.Column(db.String(100), nullable=False)
    user_agent = db.Column(db.String(255))
    ip_address = db.Column(db.String(50))
    location = db.Column(db.String(100), default='Unknown')
    timestamp = db.Column(db.DateTime, default=jakarta_now)

class ClickLog(db.Model):
    __bind_key__ = 'admin_db'
    id = db.Column(db.Integer, primary_key=True)
    button_name = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=jakarta_now)
    
# =========================================================================
# DATABASE SHOWCASE TERPISAH (showcase.db)
# =========================================================================
class ProductionGallery(db.Model):
    __bind_key__ = 'showcase_db'
    id = db.Column(db.Integer, primary_key=True)
    title_id = db.Column(db.String(100), nullable=False)
    title_en = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.String(50), nullable=False)
    category_en = db.Column(db.String(50), nullable=False)
    image_filename = db.Column(db.String(100), nullable=False)
    description_id = db.Column(db.Text, nullable=False)
    description_en = db.Column(db.Text, nullable=False)

class WebProject(db.Model):
    __bind_key__ = 'showcase_db'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    image_filename = db.Column(db.String(100), nullable=False)
    tech_stack = db.Column(db.String(200), nullable=False)
    challenge_id = db.Column(db.Text, nullable=False)
    challenge_en = db.Column(db.Text, nullable=False)
    live_url = db.Column(db.String(200), nullable=True)
    github_url = db.Column(db.String(200), nullable=True)

# ================= 1. KONFIGURASI FLASK-LOGIN =================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))


# ================= SINKRONISASI GEOLOCATION UTAMA =================
def get_visitor_location(ip_address):
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()
        
    if not ip_address or ip_address in ['127.0.0.1', 'localhost', '::1']:
        return "Localhost (Development)"
        
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(f"https://ipapi.co/{ip_address}/json/", headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('error'):
                return "Private IP (No GeoData)"
            city = data.get('city', 'Unknown City')
            country = data.get('country_name', 'Unknown Country')
            return f"{city}, {country}"
    except Exception as e:
        print(f"Gagal melacak lokasi IP: {e}")
        
    return "Unknown Location"


# ================= 4. ROUTE PENCATAT ANALITIK (FIXED FILTER) =================
@app.before_request
def track_page_view():
    ignored_paths = ['/admin', '/static', '/api', '/contact/submit', '/robots.txt', '/sitemap.xml', '/favicon.ico']
    
    should_track = True
    for path in ignored_paths:
        if request.path.startswith(path):
            should_track = False
            break

    if should_track:
        try:
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip_address:
                ip_address = ip_address.split(',')[0].strip()

            location = get_visitor_location(ip_address)

            view = PageView(
                page_url=request.path,
                user_agent=request.user_agent.string,
                ip_address=ip_address,
                location=location 
            )
            db.session.add(view)
            db.session.commit()
            
        except Exception:
            db.session.rollback()


# ================= EMAIL NOTIFIKASI MENGGUNAKAN SENDGRID API =================
def send_email_notification(name, email, subject, message):
    api_key = os.getenv('SENDGRID_API_KEY')
    sender_email = os.getenv('SENDER_EMAIL')
    receiver_email = "danielsetiawan22@gmail.com"

    email_content = (
        f"Anda menerima pesan baru dari kontak portofolio:\n\n"
        f"Nama Pengirim: {name}\n"
        f"Email Pengirim: {email}\n"
        f"Subjek: {subject}\n\n"
        f"Isi Pesan:\n{message}"
    )

    mail = Mail(
        from_email=Email(sender_email, "Portfolio Notification"),
        to_emails=To(receiver_email),
        subject=f"[PORTFOLIO INBOX] {subject}",
        plain_text_content=Content("text/plain", email_content)
    )

    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(mail)
        print(f"Notifikasi email terkirim via SendGrid API! Status: {response.status_code}")
    except Exception as e:
        print(f"Gagal mengirim via SendGrid Web API: {e}")


# ================= 3. ROUTE LOGIN ADMIN =================
@app.route('/admin')
def admin_index():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = AdminUser.query.filter_by(username=username).first()
        
        if admin and check_password_hash(admin.password_hash, password):
            login_user(admin)
            return redirect(url_for('admin_dashboard'))
            
        flash('Username atau password salah!', 'error')
        
    return render_template('admin_login.html')

@app.route('/api/track-click', methods=['POST'])
def track_click():
    data = request.get_json() or {}
    button = data.get('button')

    if button in ['facebook', 'instagram', 'github', 'email', 'linkedin']:
        try:
            log = ClickLog(button_name=button)
            db.session.add(log)
            db.session.commit()
            return jsonify({"status": "success"}), 200
        except Exception:
            db.session.rollback()
    return jsonify({"status": "error"}), 400

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    total_views = PageView.query.count()
    recent_views = PageView.query.order_by(PageView.timestamp.desc()).limit(50).all()
    
    click_stats = db.session.query(
        ClickLog.button_name, func.count(ClickLog.id)
    ).group_by(ClickLog.button_name).all()
    clicks_data = {item[0]: item[1] for item in click_stats}
    
    views_raw = PageView.query.all()
    device_data = {"Mobile": 0, "Desktop": 0}
    for v in views_raw:
        ua = v.user_agent.lower() if v.user_agent else ""
        if "mobile" in ua or "android" in ua or "iphone" in ua:
            device_data["Mobile"] += 1
        else:
            device_data["Desktop"] += 1

    profile = ProfileSection.query.first()
    experiences = Experience.query.order_by(Experience.start_date.desc()).all()
    skills = Skill.query.order_by(Skill.id.desc()).all()
    achievements = Achievement.query.order_by(Achievement.id.desc()).all()

    gallery_items = ProductionGallery.query.order_by(ProductionGallery.id.desc()).all()
    web_projects = WebProject.query.order_by(WebProject.id.desc()).all()

    return render_template('admin_dashboard.html', 
                           messages=messages, 
                           total_views=total_views, 
                           recent_views=recent_views,
                           clicks_data=clicks_data, 
                           device_data=device_data,
                           profile=profile,
                           experiences=experiences,
                           skills=skills,
                           achievements=achievements,
                           gallery=gallery_items,     
                           projects=web_projects)     

@app.route('/admin/message/delete/<int:id>', methods=['POST'])
@login_required
def delete_message(id):
    msg = ContactMessage.query.get_or_404(id)
    try:
        db.session.delete(msg)
        db.session.commit()
        return jsonify({"status": "success", "message": "Pesan berhasil dihapus."}), 200
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Gagal menghapus pesan."}), 500

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

# ================= ROUTE VIEW CMS EDITOR RESUME =================
@app.route('/admin/edit-content')
@login_required
def admin_edit_content():
    profile = ProfileSection.query.first() or ProfileSection(bio_id="", bio_en="")
    experiences = Experience.query.order_by(Experience.start_date.desc()).all()
    skills = Skill.query.order_by(Skill.id.desc()).all() 
    achievements = Achievement.query.order_by(Achievement.id.desc()).all()
    
    return render_template('admin_edit.html', 
                           profile=profile, 
                           experiences=experiences, 
                           skills=skills, 
                           achievements=achievements)

# ================= ROUTE VIEW CMS EDITOR SHOWCASE TERPISAH =================
@app.route('/admin/edit-showcase')
@login_required
def admin_edit_showcase():
    gallery_items = ProductionGallery.query.order_by(ProductionGallery.id.desc()).all()
    web_projects = WebProject.query.order_by(WebProject.id.desc()).all()
    
    return render_template('admin_edit_showcase.html', 
                           gallery=gallery_items, 
                           projects=web_projects)
                           
@app.route('/admin/get-data/<type>/<id>', methods=['GET'])
@login_required
def admin_get_data(type, id):
    if type == 'experience':
        exp = Experience.query.get_or_404(id)
        return jsonify({
            "id": exp.id,
            "company": exp.company,
            "tech_stack": exp.tech_stack,
            "title_id": exp.title_id,
            "title_en": exp.title_en,
            "description_id": exp.description_id,
            "description_en": exp.description_en,
            "start_date": exp.start_date.strftime('%Y-%m-%d') if exp.start_date else "",
            "end_date": exp.end_date.strftime('%Y-%m-%d') if exp.end_date else ""
        })
        
    elif type == 'skill':
        sk = Skill.query.get_or_404(id)
        return jsonify({
            "id": sk.id,
            "category": sk.category,
            "name_id": sk.name_id,
            "level_id": sk.level_id,
            "level_en": sk.level_en
        })
        
    elif type == 'achievement':
        ac = Achievement.query.get_or_404(id)
        return jsonify({
            "id": ac.id,
            "type": ac.type,
            "text_id": ac.text_id,
            "text_en": ac.text_en,
            "subtext_id": ac.subtext_id,
            "subtext_en": ac.subtext_en
        })

    # FIX: Menambahkan data lampiran balik JSON untuk showcase cetak & aplikasi web
    elif type == 'production':
        prod = ProductionGallery.query.get_or_404(id)
        return jsonify({
            "id": prod.id,
            "title_id": prod.title_id,
            "title_en": prod.title_en,
            "category_id": prod.category_id,
            "category_en": prod.category_en,
            "description_id": prod.description_id,
            "description_en": prod.description_en
        })

    elif type == 'web':
        web = WebProject.query.get_or_404(id)
        return jsonify({
            "id": web.id,
            "title": web.title,
            "tech_stack": web.tech_stack,
            "challenge_id": web.challenge_id,
            "challenge_en": web.challenge_en,
            "live_url": web.live_url,
            "github_url": web.github_url
        })
        
    return jsonify({"status": "error", "message": "Invalid type"}), 400

@app.route('/admin/skill/save', methods=['POST'])
@login_required
def save_skill():
    try:
        skill_id = request.form.get('id')
        
        # Validasi aman untuk menangani ID kosong atau ID bertuliskan 'new'
        if skill_id and skill_id != 'new' and skill_id.strip() != '':
            skill = Skill.query.get_or_404(int(skill_id))
        else:
            skill = Skill()
            db.session.add(skill)
            
        skill.category = request.form.get('category')
        skill.name_id = request.form.get('name_id')
        
        # PERBAIKAN: Isi name_en menggunakan fallback name_id jika input HTML-nya tidak ada
        skill.name_en = request.form.get('name_en') or request.form.get('name_id')
        
        skill.level_id = request.form.get('level_id')
        skill.level_en = request.form.get('level_en')
        
        db.session.commit()
        return jsonify({"status": "success", "message": "Keahlian berhasil disimpan!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Gagal menyimpan: {str(e)}"})

@app.route('/admin/achievement/save', methods=['POST'])
@login_required
def save_achievement():
    ach_id = request.form.get('id')
    ach = Achievement.query.get(ach_id) if ach_id else Achievement()
    if not ach_id: db.session.add(ach)
    
    ach.type = request.form.get('type')
    ach.text_id = request.form.get('text_id')
    ach.text_en = request.form.get('text_en')
    ach.subtext_id = request.form.get('subtext_id')
    ach.subtext_en = request.form.get('subtext_en')
    
    db.session.commit()
    return jsonify({"status": "success", "message": "Prestasi/Organisasi berhasil disimpan!"}), 200

@app.route('/admin/update-bio', methods=['POST'])
@login_required
def update_bio():
    profile = ProfileSection.query.first()
    if not profile:
        profile = ProfileSection()
        db.session.add(profile)
        
    profile.bio_id = request.form.get('bio_id')
    profile.bio_en = request.form.get('bio_en')
    db.session.commit()
    return jsonify({"status": "success", "message": "Bio berhasil diperbarui!"}), 200

@app.route('/admin/experience/save', methods=['POST'])
@login_required
def save_experience():
    try:
        exp_id = request.form.get('id')
        
        if exp_id:
            exp = Experience.query.get_or_404(exp_id)
        else:
            exp = Experience()
            db.session.add(exp)
            
        exp.title_id = request.form.get('title_id')
        exp.title_en = request.form.get('title_en')
        exp.company = request.form.get('company')
        exp.description_id = request.form.get('description_id')
        exp.description_en = request.form.get('description_en')
        exp.tech_stack = request.form.get('tech_stack')
        
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        # Fungsi helper internal untuk mendeteksi berbagai format tanggal browser
        def parse_date_flexible(date_str):
            if not date_str:
                return None
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y'):
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            raise ValueError(f"Format tanggal '{date_str}' tidak dikenali sistem")

        if start_date_str:
            exp.start_date = parse_date_flexible(start_date_str)
        if end_date_str:
            exp.end_date = parse_date_flexible(end_date_str)
        else:
            exp.end_date = None
            
        db.session.commit()
        return jsonify({"status": "success", "message": "Data pengalaman kerja disimpan!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Gagal menyimpan: {str(e)}"}), 500
    
@app.route('/admin/showcase/production/save', methods=['POST'])
@login_required
def save_production():
    try:
        prod_id = request.form.get('id')
        if prod_id:
            new_item = ProductionGallery.query.get_or_404(prod_id)
        else:
            new_item = ProductionGallery()
            db.session.add(new_item)

        new_item.title_id = request.form.get('title_id')
        new_item.title_en = request.form.get('title_en')
        new_item.category_id = request.form.get('category_id')
        new_item.category_en = request.form.get('category_en')
        new_item.description_id = request.form.get('description_id')
        new_item.description_en = request.form.get('description_en')
        
        file = request.files.get('image_file')
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(f"prod_{jakarta_now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_item.image_filename = filename
        elif not prod_id:
            new_item.image_filename = "default_placeholder.png" 
            
        db.session.commit()
        return jsonify({"status": "success", "message": "Item produksi berhasil disimpan!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Gagal menyimpan: {str(e)}"}), 500

@app.route('/admin/showcase/web/save', methods=['POST'])
@login_required
def save_web_project():
    try:
        web_id = request.form.get('id')
        if web_id:
            new_project = WebProject.query.get_or_404(web_id)
        else:
            new_project = WebProject()
            db.session.add(new_project)

        new_project.title = request.form.get('title')
        new_project.tech_stack = request.form.get('tech_stack')
        new_project.challenge_id = request.form.get('challenge_id')
        new_project.challenge_en = request.form.get('challenge_en')
        new_project.live_url = request.form.get('live_url')
        new_project.github_url = request.form.get('github_url')
        
        file = request.files.get('image_file')
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(f"web_{jakarta_now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_project.image_filename = filename
        elif not web_id:
            new_project.image_filename = "default_placeholder.png" 
            
        db.session.commit()
        return jsonify({"status": "success", "message": "Proyek web berhasil disimpan!"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Gagal menyimpan: {str(e)}"}), 500
        
        # =========================================================================
# ROUTE HAPUS DATA RESUME
# =========================================================================
@app.route('/admin/experience/delete/<int:id>', methods=['POST'])
@login_required
def delete_experience(id):
    try:
        exp = Experience.query.get_or_404(id)
        db.session.delete(exp)
        db.session.commit()
        return jsonify({"status": "success", "message": "Pengalaman kerja berhasil dihapus!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Gagal menghapus: {str(e)}"}), 500

@app.route('/admin/skill/delete/<int:id>', methods=['POST'])
@login_required
def delete_skill(id):
    try:
        sk = Skill.query.get_or_404(id)
        db.session.delete(sk)
        db.session.commit()
        return jsonify({"status": "success", "message": "Keahlian berhasil dihapus!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Gagal menghapus: {str(e)}"}), 500

@app.route('/admin/achievement/delete/<int:id>', methods=['POST'])
@login_required
def delete_achievement(id):
    try:
        ach = Achievement.query.get_or_404(id)
        db.session.delete(ach)
        db.session.commit()
        return jsonify({"status": "success", "message": "Prestasi/Organisasi berhasil dihapus!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Gagal menghapus: {str(e)}"}), 500

# =========================================================================
# ROUTE HAPUS DATA SHOWCASE
# =========================================================================
@app.route('/admin/showcase/production/delete/<int:id>', methods=['POST'])
@login_required
def delete_production(id):
    try:
        prod = ProductionGallery.query.get_or_404(id)
        # Hapus berkas gambar fisiknya jika bukan default placeholder
        if prod.image_filename and prod.image_filename != "default_placeholder.png":
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], prod.image_filename)
            if os.path.exists(img_path):
                os.remove(img_path)
        db.session.delete(prod)
        db.session.commit()
        return jsonify({"status": "success", "message": "Item produksi berhasil dihapus!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Gagal menghapus: {str(e)}"}), 500

@app.route('/admin/showcase/web/delete/<int:id>', methods=['POST'])
@login_required
def delete_web_project(id):
    try:
        web = WebProject.query.get_or_404(id)
        if web.image_filename and web.image_filename != "default_placeholder.png":
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], web.image_filename)
            if os.path.exists(img_path):
                os.remove(img_path)
        db.session.delete(web)
        db.session.commit()
        return jsonify({"status": "success", "message": "Proyek web berhasil dihapus!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Gagal menghapus: {str(e)}"}), 500
        
# Kamus Teks Multibahasa
MULTILINGUAL_DATA = {
    "id": {
        "name": "Daniel Setiawan",
        "title": "General Manager at Surya Abadi Printing",
        "bio": "Profesional dinamis dengan lebih dari 10 tahun pengalaman di industri percetakan & pengemasan, spesialisasi dalam cetak stiker vinyl statis. Berpengalaman meningkatkan efisiensi operasional dan strategi berbasis analisis data.",
        "meta_title": "Daniel Setiawan | Portofolio, Spesialis Percetakan, dan Digital Enthusiast",
        "meta_desc": "Portofolio profesional Daniel Setiawan, General Manager di Surya Abadi Printing. Ahli dalam manajemen operasional cetak stiker vinyl, digital marketing, dan web development.",
        "current_lang": "id", "switch_lang_text": "Switch to English", "switch_lang_code": "en"
    },
    "en": {
        "name": "Daniel Setiawan",
        "title": "General Manager at Surya Abadi Printing",
        "bio": "Dynamic and synergistic professional with over 10 years of experience in the printing and packaging industry, specializing in static vinyl sticker print. Expert in driving operational efficiency and data analytics.",
        "meta_title": "Daniel Setiawan | Portfolio, Printing Specialist, and Digital Enthusiast",
        "meta_desc": "Professional portfolio of Daniel Setiawan, General Manager at Surya Abadi Printing. Specialized in vinyl sticker printing production, data analytics, and frontend development.",
        "current_lang": "en", "switch_lang_text": "Ubah ke Bahasa Indonesia", "switch_lang_code": "id"
    }
}

RESUME_TEXTS = {
    "id": {
        "back_hub": "Kembali ke Hub", 
        "about_tag": "Tentang Saya", 
        "bio": "Profesional dinamis dengan lebih dari 7 tahun pengalaman di industri percetakan & pengemasan, spesialisasi dalam cetak stiker vinyl statis. Berpengalaman meningkatkan efisiensi operasional dan strategi berbasis analisis data.",
        "skills_title": "Keahlian Utama", 
        "history_title": "Riwayat Profesional", 
        "org_title": "Organisasi", 
        "achieve_title": "Penghargaan & Sertifikasi",
        "meta_title": "Resume Daniel Setiawan | General Manager Percetaka Surya Abadi Printing, Pengembang Web Independen, and Digital Enthusiast",
        "meta_desc": "Riwayat hidup dan pengalaman profesional Daniel Setiawan sebagai General Manager Surya Abadi Printing dan Frontend Developer. Spesialisasi manajemen cetak stiker & analisis data bisnis.",
        "current_lang": "id", 
        "switch_lang_code": "en"
    },
    "en": {
        "back_hub": "Back to Hub", 
        "about_tag": "About Me", 
        "bio": "Dynamic and synergistic professional with 7+ years of experience in the printing and packaging industry, specializing in static vinyl sticker print. Expert in driving operational efficiency and data analytics.",
        "skills_title": "Core Expertise", 
        "history_title": "Professional Experience", 
        "org_title": "Organizations", 
        "achieve_title": "Awards & Certifications",
        "meta_title": "Daniel Setiawan's Resume | General Manager of Surya Abadi Printing, Independent Web Developer, and Digital Enthusiast",
        "meta_desc": "Professional resume of Daniel Setiawan, General Manager at Surya Abadi Printing. Detailed history in operations management, data analytics, and modern web engineering.",
        "current_lang": "en", 
        "switch_lang_code": "id"
    }
}

CONTACT_TEXTS = {
    "id": {
        "meta_title": "Hubungi Daniel Setiawan | Hubungi via Email",
        "meta_desc": "Kirimkan penawaran proyek, diskusi bisnis, atau peluang kerja langsung kepada Daniel Setiawan melalui formulir kontak resmi di sini.",
        "title": "Hubungi Saya",
        "subtitle": "Kirimkan pesan, pertanyaan, atau peluang kolaborasi bisnis Anda di sini.",
        "label_name": "Nama Lengkap",
        "label_email": "Alamat Email",
        "label_subject": "Subjek / Perihal",
        "label_message": "Isi Pesan",
        "btn_send": "Kirim Pesan",
        "btn_sending": "Mengirim...",
        "current_lang": "id",
        "switch_lang_code": "en"
    },
    "en": {
        "meta_title": "Contact Daniel Setiawan | Get in Touch",
        "meta_desc": "Send project inquiries, business discussions, or career opportunities directly to Daniel Setiawan via the official contact form here.",
        "title": "Get In Touch",
        "subtitle": "Send your messages, inquiries, or business collaboration opportunities here.",
        "label_name": "Full Name",
        "label_email": "Email Address",
        "label_subject": "Subject",
        "label_message": "Message Content",
        "btn_send": "Send Message",
        "btn_sending": "Sending...",
        "current_lang": "en",
        "switch_lang_code": "id"
    }
}

# ================= RUTE HALAMAN UTAMA HUB =================
@app.route('/')
def home():
    lang = request.args.get('lang', 'id')
    if lang not in MULTILINGUAL_DATA: lang = 'id'
    profile_data = MULTILINGUAL_DATA[lang].copy()
    profile_data["links"] = [
        {
            "name": "Find Out About Me" if lang == "en" else "Ketahui Tentang Saya", 
            "url": f"/resume?lang={lang}", 
            "icon": "fas fa-file-invoice", 
            "is_internal": True,
            "subtext": "Read my professional resume & history" if lang == "en" else "Baca riwayat hidup & pengalaman profesional saya"
        },
        {
            "name": "My Showcase" if lang == "en" else "Showcase Saya", 
            "url": f"/showcase?lang={lang}", 
            "icon": "fas fa-shapes", 
            "is_internal": True,
            "subtext": "View print productions & web applications" if lang == "en" else "Lihat hasil cetak produksi & aplikasi web"
        },
        {
            "name": "Check my GitHub" if lang == "en" else "Lihat GitHub Saya", 
            "url": "https://github.com/danielsetiawan22", 
            "icon": "fab fa-github", 
            "is_internal": False,
            "subtext": "Explore my open-source repositories" if lang == "en" else "Eksplorasi repositori kode terbuka saya"
        },
        {
            "name": "Let's Connect!" if lang == "en" else "Mari Berdiskusi", 
            "url": f"/contact?lang={lang}", 
            "icon": "fas fa-envelope", 
            "is_internal": True,
            "subtext": "Send project inquiries or business discussions" if lang == "en" else "Kirimkan penawaran proyek atau diskusi bisnis"
        }
    ]
    return render_template('index.html', user=profile_data)

@app.route('/resume')
def resume_page():
    lang = request.args.get('lang', 'id')
    if lang not in ['id', 'en']: lang = 'id'
    ui = RESUME_TEXTS[lang]

    profile_db = ProfileSection.query.first()
    if profile_db:
        ui['bio'] = profile_db.bio_id if lang == 'id' else profile_db.bio_en

    user_data = {"name": "Daniel Setiawan", "current_lang": lang}

    experiences = Experience.query.order_by(Experience.id.asc()).all()
    skills = Skill.query.order_by(Skill.id.asc()).all()
    achievements_data = Achievement.query.order_by(Achievement.id.desc()).all()

    return render_template('resume.html', ui=ui, user=user_data, experiences=experiences, skills=skills, achievements=achievements_data)

@app.route('/showcase')
def showcase_page():
    lang = request.args.get('lang', 'id')
    if lang not in ['id', 'en']: lang = 'id'
    
    gallery_items = ProductionGallery.query.order_by(ProductionGallery.id.desc()).all()
    web_projects = WebProject.query.order_by(WebProject.id.desc()).all()
    
    nav_texts = {
        "id": {"title": "Showcase Portofolio", "back": "Kembali ke Hub", "subtitle": "Eksplorasi karya produksi cetak skala nasional dan pengembangan aplikasi web modern."},
        "en": {"title": "Portfolio Showcase", "back": "Back to Hub", "subtitle": "Exploration of national-scale print production and modern web engineering."}
    }
    
    return render_template('showcase.html', 
                           gallery=gallery_items, 
                           projects=web_projects, 
                           lang=lang, 
                           ui=nav_texts[lang])

@app.route('/contact', methods=['GET'])
def contact_page():
    lang = request.args.get('lang', 'id')
    if lang not in ['id', 'en']:
        lang = 'id'
    ui = CONTACT_TEXTS[lang]
    return render_template('contact.html', ui=ui)

@app.route('/robots.txt')
def robots():
    return "User-agent: *\nDisallow: /admin\nSitemap: https://danielsetiawan.com/sitemap.xml", 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://www.danielsetiawan.com/</loc><priority>1.0</priority></url>
        <url><loc>https://www.danielsetiawan.com/resume</loc><priority>0.8</priority></url>
        <url><loc>https://www.danielsetiawan.com/showcase</loc><priority>0.8</priority></url>
    </urlset>
    """
    return xml, 200, {'Content-Type': 'application/xml'}

if __name__ == '__main__':
    app.run(debug=True, port=8100)