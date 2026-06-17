import sqlite3
import re
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
DB_NAME = "resume.db"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'surya-abadi-printing-app-key-2026-super-secret!'
db = SQLAlchemy(app)

# Regex standar internasional untuk validasi email
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# ================= 1. KONFIGURASI FLASK-LOGIN =================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login' # Redirect ke halaman login jika belum autentikasi

# ================= 2. MODEL USER ADMIN =================
class AdminUser(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

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
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Tarik semua pesan dari database, urutkan dari yang terbaru
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin_dashboard.html', messages=messages)

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

with app.app_context():
    db.create_all()  # Ini memastikan tabel contact_message otomatis dibuat jika belum ad

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT, title_id TEXT, title_en TEXT,
            company TEXT, period TEXT, description_id TEXT, description_en TEXT, tech_stack TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT,
            name_id TEXT, name_en TEXT, level_id TEXT, level_en TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT, text_id TEXT, text_en TEXT, subtext_id TEXT, subtext_en TEXT
        )
    ''')
    
    cursor.execute("DELETE FROM experiences")
    cursor.execute("DELETE FROM skills")
    cursor.execute("DELETE FROM achievements")
    
    work_exp = [
        ('printing', 'General Manager', 'General Manager', 'Surya Abadi Printing', 'Feb 2023 - Present', 'Memimpin inisiatif pertumbuhan bisnis dan strategi operasional. Mengelola anggaran tahunan sebesar Rp 2 Miliar, berhasil memotong biaya 15% serta menaikkan pendapatan 20%. Membangun sistem penjadwalan yang mengurangi komplain kualitas sebesar 25% dan menaikkan efisiensi operasional 20%. Mengoordinasikan 15 supplier untuk memastikan 98% on-time delivery. Menjaga retensi pelanggan hingga meningkat 15% dengan tingkat kepuasan 95% untuk klien strategis seperti Suzuki, Toyota Accessories, Solar Gard, Sandei Blinds, JP Helmet, KYT & INK, NHK, GM, MAZ, VOG.', 'Spearheaded business growth initiatives, developed operational strategies, and oversaw end-to-end operations. Successfully managed Rp 2 billion annual budgets, reducing expenses by 15% while increasing revenue by 20%. Established a scheduling system to reduce quality conflicts by 25%, boosting operational efficiency by 20%. Coordinated with 15 suppliers to ensure 98% on-time delivery. Maintained strategic client relationships, resulting in a 15% increase in customer retention and 95% satisfaction rate for key clients (Suzuki, Toyota Accessories, Solar Gard, Sandei Blinds, JP Helmet, KYT & INK, NHK, GM, MAZ, VOG).', 'Operations Management, Strategic Procurement, Cost-Saving, Team Leadership, Budgeting'),
        ('printing', 'Manajer Operasional', 'Operations Manager', 'Surya Abadi Printing', 'Feb 2019 - Jan 2023', 'Mengarahkan operasional harian perusahaan meliputi perencanaan produksi, kontrol kualitas (QC), manajemen inventaris, dan alokasi sumber daya. Berhasil mengidentifikasi inefisiensi operasional dan menyarankan langkah korektif yang memotong biaya sebesar 10%. Menegosiasikan kontrak menguntungkan dengan supplier, mengoptimalkan proses pengadaan, dan berhasil mengurangi lead time sebesar 15% untuk penanganan klien utama.', 'Directed day-to-day operations, including production planning, quality control, inventory management, and resource allocation. Established and maintained rigorous quality control processes. Identified operational inefficiencies and suggested corrective measures that resulted in a 10% cost reduction. Negotiated favorable contracts with suppliers, optimized procurement processes, and reduced lead times by 15%.', 'Production Planning, Quality Control, Inventory Management, Supplier Negotiation, Lead Time Reduction'),
        ('printing', 'Analis Operasional', 'Operations Analyst', 'Surya Abadi Printing', 'Dec 2016 - Jan 2019', 'Menganalisis data operasional dan dinamika rantai pasok untuk mengidentifikasi inefisiensi. Mengimplementasikan perbaikan proses yang menghasilkan penurunan biaya sebesar 10% dan pengurangan lead time sebesar 5%. Memproduksi 20 laporan operasional berbasis data untuk memandu pengambilan keputusan strategis. Menangani akuisisi klien penting seperti Kue Lily, Heisz Medical, Corner Kebab, AmerthaGracia, McDonalds, dan Vendor Kotak Katering Pre-Asian Games 2018.', 'Analyzed operational data, identifying inefficiencies, and providing data-driven recommendations. Analyzed supply chain dynamics and optimized procurement strategies. Implemented process improvements leading to a 10% cost reduction and 5% reduction in lead times. Produced 20 data-based operational reports. Handled notable client acquisition (Kue Lily, Heisz Medical, Corner Kebab, AmerthaGracia, McDonalds, Pre-Asian Games 2018 Catering Box Vendor).', 'Data Analysis, Supply Chain Optimization, Process Improvement, Operational Reporting'),
        ('web', 'Frontend Web Developer', 'Frontend Web Developer', 'UNIXON BRANDING', 'Jan 2014 - Nov 2016', 'Merencanakan, membuat kode, mendesain, dan menyusun tata letak situs web sesuai kebutuhan klien. Berhasil mengembangkan, memperluas, dan memperbaiki lebih dari 30 situs web untuk UMKM dengan memanfaatkan teknologi HTML, CSS, JavaScript, MySQL, dan Bootstrap, serta memimpin pengujian responsivitas dan kompatibilitas lintas browser.', 'Planned, coded, designed, and laid out websites to fulfill client requirements. Developed, expanded, and rectified over 30 websites for SMEs, employing HTML, CSS, JavaScript, MySQL, and Bootstrap technologies. Supervised procedures for cross-browser compatibility and responsiveness testing.', 'HTML5, CSS3, JavaScript, Bootstrap, MySQL, Cross-Browser Testing'),
        ('education', 'Mentor Data Analytics', 'Data Analytics Mentor', 'Bitlabs Academy', 'Apr 2024 - Dec 2024', 'Dipercaya sebagai Mentor Data Analytics untuk program Data Analytics for Business 2024 Kampus Merdeka Batch 7. Membimbing individu serta tim dalam peningkatan keahlian analisis, mengelola program pelatihan, dan memberikan dukungan teknis pemecahan masalah data aplikasi bisnis.', 'Appointed as a Mentor of Data Analytics for Business 2024 Kampus Merdeka Batch 7. Mentored individuals and teams in data analysis, emphasizing skill enhancement. Managed training programs to ensure comprehension of fundamental and advanced data analysis concepts.', 'Data Analysis, Business Data Applications, Training & Mentoring')
    ]
    cursor.executemany("INSERT INTO experiences (category, title_id, title_en, company, period, description_id, description_en, tech_stack) VALUES (?,?,?,?,?,?,?,?)", work_exp)
    
    skills_list = [
        ('tech', 'Product Management', 'Product Management', 'Ahli', 'Expert'),
        ('tech', 'Digital Marketing', 'Digital Marketing', 'Lanjutan', 'Advanced'),
        ('tech', 'R Programming', 'R Programming', 'Menengah', 'Intermediate'),
        ('tech', 'HTML / CSS / JS', 'HTML / CSS / JS', 'Ahli', 'Expert'),
        ('prod', 'Cetak Stiker Vinyl Statis', 'Specialized Static Vinyl Sticker Printing', 'Ahli', 'Expert'),
        ('prod', 'Analisis Data & KPI', 'Data Analytics & KPI Management', 'Ahli', 'Expert')
    ]
    cursor.executemany("INSERT INTO skills (category, name_id, name_en, level_id, level_en) VALUES (?,?,?,?,?)", skills_list)

    achievements_list = [
        ('org', 'Ketua Komite 100% Efficiency, KPI & Awarding', '100% Efficiency, KPI & Awarding Committee Chairperson', 'JCI Indonesia', 'JCI Indonesia'),
        ('award', 'Juara Tingkat Nasional Teras Usaha Mahasiswa', 'Teras Usaha Mahasiswa National Champion', 'Bank BRI', 'National Champion'),
        ('award', 'Pemenang Regional Teras Usaha Mahasiswa - Jakarta', 'Teras Usaha Mahasiswa Regional Winner - Jakarta', 'Bank BRI', 'Regional Winner'),
        ('award', 'Juara Dua DBS BIG Competition', 'DBS BIG Competition Runner Up Champion', 'DBS Bank', 'Runner Up Champion'),
        ('award', 'Lulusan dengan Predikat Magna Cum Laude', 'Magna Cum Laude Graduate', 'Universitas Prasetiya Mulya', 'Academic Honors'),
        ('pub', 'Studi Kelayakan Usaha Percetakan Mandiri: Copycino Business Project', 'Studi Kelayakan Usaha Percetakan Mandiri: Copycino Business Project', 'Publikasi Internal / Proyek', 'Business Project Publication'),
        ('cert', 'Analisis Data dengan Pemrograman R', 'Data Analysis with R Programming', 'Sertifikasi Kompetensi', 'Professional Certification')
    ]
    cursor.executemany("INSERT INTO achievements (type, text_id, text_en, subtext_id, subtext_en) VALUES (?,?,?,?,?)", achievements_list)
    
    conn.commit()
    conn.close()

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

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
             
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

@app.route('/resume')
def resume():
    lang = request.args.get('lang', 'id')
    if lang not in RESUME_TEXTS: lang = 'id'
    ui_text = RESUME_TEXTS[lang]
    
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM experiences ORDER BY id ASC")
    experiences = cursor.fetchall()
    cursor.execute("SELECT * FROM skills")
    skills = cursor.fetchall()
    cursor.execute("SELECT * FROM achievements ORDER BY id ASC")
    achievements = cursor.fetchall()
    conn.close()
    
    user_data = {"name": "Daniel Setiawan"}
    return render_template('resume.html', experiences=experiences, skills=skills, achievements=achievements, ui=ui_text, user=user_data)
    
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
    init_db()
    app.run(debug=True, port=8100)