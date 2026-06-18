from app import app, db, ProfileSection, Experience, Skill, Achievement, AdminUser
from werkzeug.security import generate_password_hash
from datetime import date

def seed_database():
    with app.app_context():
        # Membuat database baru dengan skema mutakhir (database.db & admin.db)
        db.create_all()
        print("Successfully initialized both database.db and admin.db files!")
        
        # ================= 1. SEEDING USER ADMIN (Ke admin.db otomatis karena bind_key) =================
        if AdminUser.query.count() == 0:
            hashed_password = generate_password_hash("admin")
            admin_user = AdminUser(username="admin", password_hash=hashed_password)
            db.session.add(admin_user)
            print("Successfully seeded AdminUser with hashed password into admin.db!")
            
        # ================= 2. SEEDING TENTANG SAYA (PROFILE/BIO) =================
        if ProfileSection.query.count() == 0:
            default_bio = ProfileSection(
                bio_id="Profesional dinamis dengan lebih dari 7 tahun pengalaman di industri percetakan & pengemasan, spesialisasi dalam cetak stiker vinyl statis. Berpengalaman meningkatkan efisiensi operasional dan strategi berbasis analisis data.",
                bio_en="Dynamic professional with over 7 years of experience in the printing & packaging industry, specializing in static vinyl sticker printing. Experienced in boosting operational efficiency and data-driven strategies."
            )
            db.session.add(default_bio)
            print("Successfully seeded Profile Bio!")

        # ================= 3. SEEDING DATA PENGALAMAN KERJA (EXPERIENCES) =================
        # Parameter 'period' diganti menjadi 'start_date' dan 'end_date' bertipe date untuk akurasi kronologis
        if Experience.query.count() == 0:
            work_exp = [
                Experience(
                    title_id='General Manager', 
                    title_en='General Manager', 
                    company='Surya Abadi Printing', 
                    start_date=date(2023, 2, 1), 
                    end_date=None,  # None dihitung sebagai NULL / "Present"
                    description_id='Memimpin inisiatif pertumbuhan bisnis dan strategi operasional. Mengelola anggaran tahunan sebesar Rp 2 Miliar, berhasil memotong biaya 15% serta menaikkan pendapatan 20%. Membangun sistem penjadwalan yang mengurangi komplain kualitas sebesar 25% dan menaikkan efisiensi operasional 20%. Mengoordinasikan 15 supplier untuk memastikan 98% on-time delivery. Menjaga retensi pelanggan hingga meningkat 15% dengan tingkat kepuasan 95% untuk klien strategis seperti Suzuki, Toyota Accessories, Solar Gard, Sandei Blinds, JP Helmet, KYT & INK, NHK, GM, MAZ, VOG.',
                    description_en='Spearheaded business growth initiatives, developed operational strategies, and oversaw end-to-end operations. Successfully managed Rp 2 billion annual budgets, reducing expenses by 15% while increasing revenue by 20%. Established a scheduling system to reduce quality conflicts by 25%, boosting operational efficiency by 20%. Coordinated with 15 suppliers to ensure 98% on-time delivery. Maintained strategic client relationships, resulting in a 15% increase in customer retention and 95% satisfaction rate for key clients.',
                    tech_stack='Operations Management, Strategic Procurement, Cost-Saving, Team Leadership, Budgeting'
                ),
                Experience(
                    title_id='Mentor Data Analytics', 
                    title_en='Data Analytics Mentor', 
                    company='Bitlabs Academy', 
                    start_date=date(2024, 4, 1), 
                    end_date=date(2024, 12, 1),
                    description_id='Dipercaya sebagai Mentor Data Analytics untuk program Data Analytics for Business 2024 Kampus Merdeka Batch 7. Membimbing individu serta tim dalam peningkatan keahlian analisis, mengelola program pelatihan, dan memberikan dukungan teknis pemecahan masalah data aplikasi bisnis.',
                    description_en='Appointed as a Mentor of Data Analytics for Business 2024 Kampus Merdeka Batch 7. Mentored individuals and teams in data analysis, emphasizing skill enhancement. Managed training programs to ensure comprehension of fundamental and advanced data analysis concepts.',
                    tech_stack='Data Analysis, Business Data Applications, Training & Mentoring'
                ),
                Experience(
                    title_id='Manajer Operasional', 
                    title_en='Operations Manager', 
                    company='Surya Abadi Printing', 
                    start_date=date(2019, 2, 1), 
                    end_date=date(2023, 1, 1),
                    description_id='Mangarahkan operasional harian perusahaan meliputi perencanaan produksi, kontrol kualitas (QC), manajemen inventaris, dan alokasi sumber daya. Berhasil mengidentifikasi inefisiensi operasional dan menyarankan langkah korektif yang memotong biaya sebesar 10%. Menegosiasikan kontrak menguntungkan dengan supplier, mengoptimalkan proses pengadaan, dan berhasil mengurangi lead time sebesar 15% untuk penanganan klien utama.',
                    description_en='Directed day-to-day operations, including production planning, quality control, inventory management, and resource allocation. Established and maintained rigorous quality control processes. Identified operational inefficiencies and suggested corrective measures that resulted in a 10% cost reduction. Negotiated favorable contracts with suppliers, optimized procurement processes, and reduced lead times by 15%.',
                    tech_stack='Production Planning, Quality Control, Inventory Management, Supplier Negotiation, Lead Time Reduction'
                ),
                Experience(
                    title_id='Analis Operasional', 
                    title_en='Operations Analyst', 
                    company='Surya Abadi Printing', 
                    start_date=date(2016, 12, 1), 
                    end_date=date(2019, 1, 1),
                    description_id='Menganalisis data operasional dan dinamika rantai pasok untuk mengidentifikasi inefisiensi. Mengimplementasikan perbaikan proses yang menghasilkan penurunan biaya sebesar 10% dan penghematan lead time sebesar 5%. Memproduksi 20 laporan operasional berbasis data untuk memandu pengambilan keputusan strategis. Menangani akuisisi klien penting seperti Kue Lily, Heisz Medical, Corner Kebab, AmerthaGracia, McDonalds, dan Vendor Kotak Katering Pre-Asian Games 2018.',
                    description_en='Analyzed operational data, identifying inefficiencies, and providing data-driven recommendations. Analyzed supply chain dynamics and optimized procurement strategies. Implemented process improvements leading to a 10% cost reduction and 5% reduction in lead times. Produced 20 data-based operational reports.',
                    tech_stack='Data Analysis, Supply Chain Optimization, Process Improvement, Operational Reporting'
                ),
                Experience(
                    title_id='Frontend Web Developer', 
                    title_en='Frontend Web Developer', 
                    company='UNIXON BRANDING', 
                    start_date=date(2014, 1, 1), 
                    end_date=date(2016, 11, 1),
                    description_id='Merencanakan, membuat kode, mendesain, dan menyusun tata letak situs web sesuai kebutuhan klien. Berhasil mengembangkan, memperluas, dan memperbaiki lebih dari 30 situs web untuk UMKM dengan memanfaatkan teknologi HTML, CSS, JavaScript, MySQL, dan Bootstrap, serta memimpin pengujian responsivitas dan kompatibilitas lintas browser.',
                    description_en='Planned, coded, designed, and laid out websites to fulfill client requirements. Developed, expanded, and rectified over 30 websites for SMEs, employing HTML, CSS, JavaScript, MySQL, and Bootstrap technologies.',
                    tech_stack='HTML5, CSS3, JavaScript, Bootstrap, MySQL, Cross-Browser Testing'
                )
            ]
            db.session.bulk_save_objects(work_exp)
            print("Successfully seeded Experiences!")

        # ================= 4. SEEDING DATA KEAHLIAN (SKILLS) =================
        if Skill.query.count() == 0:
            skills_list = [
                Skill(category='tech', name_id='Product Management', name_en='Product Management', level_id='Ahli', level_en='Expert'),
                Skill(category='tech', name_id='Digital Marketing', name_en='Digital Marketing', level_id='Lanjutan', level_en='Advanced'),
                Skill(category='tech', name_id='R Programming', name_en='R Programming', level_id='Menengah', level_en='Intermediate'),
                Skill(category='tech', name_id='HTML / CSS / JS', name_en='HTML / CSS / JS', level_id='Ahli', level_en='Expert'),
                Skill(category='prod', name_id='Cetak Stiker Vinyl Statis', name_en='Specialized Static Vinyl Sticker Printing', level_id='Ahli', level_en='Expert'),
                Skill(category='prod', name_id='Analisis Data & KPI', name_en='Data Analytics & KPI Management', level_id='Ahli', level_en='Expert')
            ]
            db.session.bulk_save_objects(skills_list)
            print("Successfully seeded Skills!")

        # ================= 5. SEEDING DATA PRESTASI & ORGANISASI (ACHIEVEMENTS) =================
        if Achievement.query.count() == 0:
            achievements_list = [
                Achievement(type='org', text_id='Ketua Komite 100% Efficiency, KPI & Awarding', text_en='100% Efficiency, KPI & Awarding Committee Chairperson', subtext_id='JCI Indonesia', subtext_en='JCI Indonesia'),
                Achievement(type='award', text_id='Juara Tingkat Nasional Teras Usaha Mahasiswa', text_en='Teras Usaha Mahasiswa National Champion', subtext_id='Bank BRI', subtext_en='National Champion'),
                Achievement(type='award', text_id='Pemenang Regional Teras Usaha Mahasiswa - Jakarta', text_en='Teras Usaha Mahasiswa Regional Winner - Jakarta', subtext_id='Bank BRI', subtext_en='Regional Winner'),
                Achievement(type='award', text_id='Juara Dua DBS BIG Competition', text_en='DBS BIG Competition Runner Up Champion', subtext_id='DBS Bank', subtext_en='Runner Up Champion'),
                Achievement(type='award', text_id='Lulusan dengan Predikat Magna Cum Laude', text_en='Magna Cum Laude Graduate', subtext_id='Universitas Prasetiya Mulya', subtext_en='Academic Honors'),
                Achievement(type='pub', text_id='Studi Kelayakan Usaha Percetakan Mandiri: Copycino Business Project', text_en='Studi Kelayakan Usaha Percetakan Mandiri: Copycino Business Project', subtext_id='Publikasi Internal / Proyek', subtext_en='Business Project Publication'),
                Achievement(type='cert', text_id='Analisis Data dengan Pemrograman R', text_en='Data Analysis with R Programming', subtext_id='Sertifikasi Kompetensi', subtext_en='Professional Certification')
            ]
            db.session.bulk_save_objects(achievements_list)
            print("Successfully seeded Achievements!")

        db.session.commit()
        print("Database seeding completed smoothly!")

if __name__ == '__main__':
    seed_database()