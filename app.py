import os
import sqlite3
import re
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import smtplib
from email.mime.text import MIMEText
import requests

app = Flask(__name__)
DB_NAME = "resume.db"

# 1. SETUP PATH DIREKTORI INSTANCE
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')

# 2. DEFINISIKAN SEMUA CONFIG URI & BINDS (WAJIB SEBELUM INSTANSIASI DB)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(INSTANCE_DIR, 'database.db')}"

app.config['SQLALCHEMY_BINDS'] = {
    'admin_db': f"sqlite:///{os.path.join(INSTANCE_DIR, 'admin.db')}",
    'contact_db': f"sqlite:///{os.path.join(INSTANCE_DIR, 'contact.db')}"
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 3. INSTANSIASI ELEMEN DB (Setelah Flask membaca konfigurasi di atas)
db = SQLAlchemy(app)
app.config['SECRET_KEY'] = 'bebas-isi-apa-saja-yang-panjang-dan-rahasia-12345'

# Regex standar internasional untuk validasi email
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

def jakarta_now():
    return datetime.now(ZoneInfo("Asia/Jakarta")).replace(tzinfo=None)

# ================= 1. KONFIGURASI FLASK-LOGIN =================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login' # Redirect ke halaman login jika belum autentikasi

# ================= MODEL USER ADMIN DI APP.PY =================
@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))

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

# ================= 4. ROUTE DASHBOARD UTAMA (TERPROTEKSI) =================

# 1. MIDDLEWARE: Lacak Kunjungan Halaman Secara Otomatis
@app.before_request
def track_page_view():
    # Hindari melacak aset statis atau rute admin agar data tidak bias
    if not request.path.startswith('/static') and not request.path.startswith('/admin'):
        try:
            view = PageView(
                page_url=request.path,
                user_agent=request.user_agent.string,
                ip_address=request.remote_addr
            )
            db.session.add(view)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()

# 2. ENDPOINT API: Ambil data Klik dari Frontend (AJAX)
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

# 3. ROUTE DASHBOARD ADMIN: Agregasi Data Untuk Grafik Chart.js
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # 1. Tarik Data Pesan dari contact.db & Analytics dari admin.db
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    total_views = PageView.query.count()
    
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

    # ================= TAMBAHKAN QUERY RESUME DI BAWAH INI =================
    profile = ProfileSection.query.first()
    experiences = Experience.query.order_by(Experience.start_date.desc()).all()
    skills = Skill.query.order_by(Skill.id.desc()).all()
    achievements = Achievement.query.order_by(Achievement.id.desc()).all()
    # =======================================================================

    # Kirimkan SELURUH variabel tersebut ke dalam satu template dashboard
    return render_template('admin_dashboard.html', 
                           messages=messages, 
                           total_views=total_views, 
                           clicks_data=clicks_data, 
                           device_data=device_data,
                           profile=profile,
                           experiences=experiences,
                           skills=skills,
                           achievements=achievements)

# ================= 5. ROUTE HAPUS PESAN (API AJAX) =================
@app.route('/admin/message/delete/<int:id>', methods=['POST'])
@login_required
def delete_message(id):
    msg = ContactMessage.query.get_or_400(id)
    try:
        db.session.delete(msg)
        db.session.commit()
        return jsonify({"status": "success", "message": "Pesan berhasil dihapus."}), 200
    except:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Gagal menghapus pesan."}), 500

# ================= 6. ROUTE LOGOUT =================
@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

# =========================================================================
# DATABASE UTAMA (database.db) - Tanpa bind_key (Default)
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
# DATABASE TERPISAH (admin.db) - Menggunakan bind_key
# =========================================================================
class AdminUser(UserMixin, db.Model):
    __bind_key__ = 'admin_db' # Tetap di admin.db
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
    timestamp = db.Column(db.DateTime, default=jakarta_now)

class ClickLog(db.Model):
    __bind_key__ = 'admin_db'
    id = db.Column(db.Integer, primary_key=True)
    button_name = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=jakarta_now)

# ================= ROUTE VIEW CMS EDITOR (REVISI LENGKAP) =================
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

# ================= 1. GET DATA UNTUK MODAL (AJAX) =================
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
            
            # === PERBAIKAN DI SINI: Paksa konversi tanggal menjadi format string YYYY-MM-DD ===
            "start_date": exp.start_date.strftime('%Y-%m-%d') if exp.start_date else "",
            "end_date": exp.end_date.strftime('%Y-%m-%d') if exp.end_date else ""
            # ================================================================================
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
        
    return jsonify({"status": "error", "message": "Invalid type"}), 400
# ================= 2. SAVE SKILL ACTION =================
@app.route('/admin/skill/save', methods=['POST'])
@login_required
def save_skill():
    skill_id = request.form.get('id')
    skill = Skill.query.get(skill_id) if skill_id else Skill()
    if not skill_id: db.session.add(skill)
    
    skill.category = request.form.get('category')
    skill.name_id = request.form.get('name_id')
    skill.name_en = request.form.get('name_en')
    skill.level_id = request.form.get('level_id')
    skill.level_en = request.form.get('level_en')
    
    db.session.commit()
    return jsonify({"status": "success", "message": "Keahlian berhasil disimpan!"}), 200

# ================= 3. SAVE ACHIEVEMENT/ORG ACTION =================
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

# ================= ACTION: UPDATE BIO =================
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

# ================= ACTION: ADD / EDIT EXPERIENCE =================
@app.route('/admin/experience/save', methods=['POST'])
@login_required
def save_experience():
    exp_id = request.form.get('id')
    
    if exp_id: # Jika ID ada, lakukan update data lama
        exp = Experience.query.get_or_404(exp_id)
    else: # Jika ID kosong, buat record pengalaman baru
        exp = Experience()
        db.session.add(exp)
        
    exp.title_id = request.form.get('title_id')
    exp.title_en = request.form.get('title_en')
    exp.company = request.form.get('company')
    exp.period = request.form.get('period')
    exp.description_id = request.form.get('description_id')
    exp.description_en = request.form.get('description_en')
    exp.tech_stack = request.form.get('tech_stack')
    
    db.session.commit()
    return jsonify({"status": "success", "message": "Data pengalaman kerja disimpan!"}), 200

# Kamus Teks Beranda Utama
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

# Kamus Teks Resume
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


             
@app.route('/')
def home():
    lang = request.args.get('lang', 'id')
    if lang not in MULTILINGUAL_DATA: lang = 'id'
    profile_data = MULTILINGUAL_DATA[lang].copy()
    profile_data["links"] = [
        {"name": "Find Out About Me" if lang == "en" else "Ketahui Tentang Saya", "url": f"/resume?lang={lang}", "icon": "fas fa-file-invoice", "is_internal": True},
        {"name": "Check my GitHub" if lang == "en" else "Lihat GitHub Saya", "url": "https://github.com/danielsetiawan22", "icon": "fab fa-github", "is_internal": False},
        {"name": "Let's Connect!" if lang == "en" else "Mari Berdiskusi", "url": f"/contact?lang={lang}", "icon": "fas fa-envelope", "is_internal": True}
    ]
    return render_template('index.html', user=profile_data)

# ================= ROUTE RESUME DENGAN DATA LENGKAP (REVISI) =================
@app.route('/resume')
def resume_page():
    lang = request.args.get('lang', 'id')
    if lang not in ['id', 'en']: lang = 'id'
    ui = RESUME_TEXTS[lang]

    profile_db = ProfileSection.query.first()
    if profile_db:
        ui['bio'] = profile_db.bio_id if lang == 'id' else profile_db.bio_en

    user_data = {"name": "Daniel Setiawan", "current_lang": lang}

    # Urutkan secara kronologis terbalik menggunakan ID desc agar sinkron dengan admin
    experiences = Experience.query.order_by(Experience.id.asc()).all()
    skills = Skill.query.order_by(Skill.id.asc()).all()
    achievements_data = Achievement.query.order_by(Achievement.id.desc()).all()

    return render_template('resume.html', ui=ui, user=user_data, experiences=experiences, skills=skills, achievements=achievements_data)

def send_email_notification(name, email, subject, message):
    # Gunakan kredensial aman (disarankan simpan di OS Environment variables)
    SENDER_EMAIL = "danielsetiawan22@gmail.com"
    SENDER_PASSWORD = "etmz dzfz jewf mrsy" 
    RECEIVER_EMAIL = "hello@danielsetiawan.com"

    msg = MIMEText(f"Nama Pengirim: {name}\nEmail: {email}\n\nPesan:\n{message}")
    msg['Subject'] = f"[PORTFOLIO INBOX] {subject}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL], msg.as_string())
    except Exception as e:
        print(f"Gagal mengirim notifikasi email: {e}")
   
@app.route('/contact', methods=['GET', 'POST'])
def contact_page():
    # Mengatur bahasa aktif
    lang = request.args.get('lang', 'id')
    if lang not in ['id', 'en']:
        lang = 'id'
    
    ui = CONTACT_TEXTS[lang]

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        # 1. Cek apakah ada field yang kosong
        if not name or not email or not subject or not message:
            err_msg = "Semua field wajib diisi!" if lang == 'id' else "All fields are required!"
            return jsonify({"status": "error", "message": err_msg}), 400

        # 2. VALIDASI EMAIL: Periksa apakah format email match dengan REGEX
        if not re.match(EMAIL_REGEX, email.strip()):
            invalid_msg = "Format alamat email tidak valid!" if lang == 'id' else "Invalid email address format!"
            return jsonify({"status": "error", "message": invalid_msg}), 400

        # 3. Jika lolos validasi, baru teruskan simpan ke database SQLite
        try:
            new_msg = ContactMessage(
                name=name, 
                email=email.strip().lower(), # Bersihkan spasi dan paksa huruf kecil
                subject=subject, 
                message=message
            )
            db.session.add(new_msg)
            db.session.commit()
            
            succ_msg = "Pesan Anda berhasil dikirim!" if lang == 'id' else "Your message has been sent successfully!"
            return jsonify({"status": "success", "message": succ_msg}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": "Database error"}), 500

    return render_template('contact.html', ui=ui)

@app.route('/contact/submit', methods=['POST'])
def contact_submit():
    # Ambil token turnstile dari form
    turnstile_response = request.form.get('cf-turnstile-response')
    
    # ==================== MATIKAN VALIDASI TURNSTILE SEMENTARA ====================
    # COMMENT ATAU MATIKAN BLOK INI:
    # payload = {
    #     'secret': 'SECRET_KEY_ANDA',
    #     'response': turnstile_response
    # }
    # verify_response = requests.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=payload)
    # outcome = verify_response.json()
    # if not outcome.get('success'):
    #     return jsonify({"status": "error", "message": "Validasi keamanan anti-bot gagal!"}), 400
    # ==============================================================================
    
    # Ambil data form seperti biasa
    name = request.form.get('name')
    email = request.form.get('email')
    subject = request.form.get('subject')
    msg_text = request.form.get('message')
    
    # Simpan ke database dengan waktu Jakarta (WIB)
    waktu_jakarta = jakarta_now()
    new_msg = ContactMessage(
        name=name,
        email=email,
        subject=subject,
        message=msg_text,
        created_at=waktu_jakarta
    )
    
    db.session.add(new_msg)
    db.session.commit()
    
    return jsonify({"status": "success", "message": "Pesan berhasil dikirim tanpa bot-check!"}), 200
        
@app.route('/robots.txt')
def robots():
    return "User-agent: *\nDisallow: /admin\nSitemap: https://danielsetiawan.com/sitemap.xml", 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    # Peta situs sederhana untuk mengarahkan Google Bot ke halaman utama dan resume
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://www.danielsetiawan.com/</loc><priority>1.0</priority></url>
        <url><loc>https://www.danielsetiawan.com/resume</loc><priority>0.8</priority></url>
    </urlset>
    """
    return xml, 200, {'Content-Type': 'application/xml'}

if __name__ == '__main__':
    app.run(debug=True, port=8100)