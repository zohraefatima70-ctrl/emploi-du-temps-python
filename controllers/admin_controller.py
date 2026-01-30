# --- Importations nécessaires ---
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from database import (
    insert_schedule_slot,
    check_conflict,
    getConnection,
    DAYS
)

# ==============================
# Contrôleur pour l'administrateur
# ==============================
class AdminController:

    def __init__(self, admin_id):
        self.admin_id = admin_id

    def creer_creneau(self, course_id, instructor_id, group_id, room_id, day, start_hour, duration):
        conflit = check_conflict(instructor_id, group_id, room_id, day, start_hour, duration)
        if conflit:
            print(f" Conflit détecté : {conflit}")
            return False
        success = insert_schedule_slot(course_id, instructor_id, group_id, room_id, day, start_hour, duration, self.admin_id)
        if success:
            print(" Créneau ajouté avec succès.")
        return success

    def valider_reservation(self, reservation_id):
        conn = getConnection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE reservations
            SET status = 'APPROVED', approved_by = ?, approved_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'PENDING'
        """, (self.admin_id, reservation_id))
        conn.commit()
        if cursor.rowcount > 0:
            print(f" Réservation {reservation_id} validée.")
        else:
            print(f" Aucune réservation en attente avec l’ID {reservation_id}.")
        conn.close()

    def rejeter_reservation(self, reservation_id):
        conn = getConnection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE reservations
            SET status = 'REJECTED', approved_by = ?, approved_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'PENDING'
        """, (self.admin_id, reservation_id))
        conn.commit()
        if cursor.rowcount > 0:
            print(f" Réservation {reservation_id} rejetée.")
        else:
            print(f" Aucune réservation en attente avec l’ID {reservation_id}.")
        conn.close()

    def afficher_details_reservation(self, reservation_id):
        conn = getConnection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.id, u.full_name AS enseignant, rm.name AS salle, g.name AS groupe,
                   r.day, r.start_hour, r.duration, r.reason, r.status
            FROM reservations r
            JOIN instructors i ON r.instructor_id = i.id
            JOIN users u ON i.user_id = u.id
            LEFT JOIN rooms rm ON r.room_id = rm.id
            LEFT JOIN groups g ON r.group_id = g.id
            WHERE r.id = ?
        """, (reservation_id,))
        res = cursor.fetchone()
        conn.close()

        if res:
            print("\n Détails de la réservation :")
            print(f"- ID : {res['id']}")
            print(f"- Enseignant : {res['enseignant']}")
            print(f"- Salle : {res['salle']}")
            print(f"- Groupe : {res['groupe']}")
            print(f"- Jour : {DAYS[res['day']]}")
            print(f"- Heure début : {res['start_hour']}h")
            print(f"- Durée : {res['duration']}h")
            print(f"- Raison : {res['reason']}")
            print(f"- Statut : {res['status']}")
        else:
            print(" Réservation introuvable.")

    def afficher_reservations_en_attente(self):
        conn = getConnection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.id, u.full_name AS enseignant, r.day, r.start_hour, r.duration, r.reason
            FROM reservations r
            JOIN instructors i ON r.instructor_id = i.id
            JOIN users u ON i.user_id = u.id
            WHERE r.status = 'PENDING'
            ORDER BY r.day, r.start_hour
        """)
        results = cursor.fetchall()
        conn.close()

        if results:
            print("\n Réservations en attente :")
            for r in results:
                print(f"- ID {r['id']} | {DAYS[r['day']]} {r['start_hour']}h-{r['start_hour']+r['duration']}h | Enseignant : {r['enseignant']} | Raison : {r['reason']}")
        else:
            print("Aucune réservation en attente.")

    def afficher_statistiques(self):
        conn = getConnection()
        cursor = conn.cursor()

        nb_creneaux = cursor.execute("SELECT COUNT(*) FROM timetable").fetchone()[0]
        nb_reservations = cursor.execute("SELECT COUNT(*) FROM reservations WHERE status = 'APPROVED'").fetchone()[0]
        nb_salles = cursor.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]

        print("\n Statistiques générales :")
        print(f"- Nombre total de créneaux planifiés : {nb_creneaux}")
        print(f"- Réservations approuvées : {nb_reservations}")
        print(f"- Nombre de salles disponibles : {nb_salles}")

        print("\n Taux d’occupation des salles :")
        cursor.execute("""
            SELECT r.name, COUNT(t.id) AS nb_creneaux
            FROM rooms r
            LEFT JOIN timetable t ON r.id = t.room_id
            GROUP BY r.id
            ORDER BY nb_creneaux DESC
        """)
        for row in cursor.fetchall():
            print(f"- {row['name']} : {row['nb_creneaux']} créneaux")

        conn.close()

    def exporter_statistiques_excel(self, filename="statistiques.xlsx"):
        conn = getConnection()
        cursor = conn.cursor()

        stats = cursor.execute("""
            SELECT r.name, COUNT(t.id) AS nb_creneaux
            FROM rooms r
            LEFT JOIN timetable t ON r.id = t.room_id
            GROUP BY r.id
        """).fetchall()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Statistiques"

        ws.append(["Salle", "Nombre de créneaux"])
        for row in stats:
            ws.append([row["name"], row["nb_creneaux"]])

        wb.save(filename)
        conn.close()
        print(f" Statistiques exportées vers {filename}")

    def exporter_statistiques_pdf(self, filename="statistiques.pdf"):
        conn = getConnection()
        cursor = conn.cursor()

        stats = cursor.execute("""
            SELECT r.name, COUNT(t.id) AS nb_creneaux
            FROM rooms r
            LEFT JOIN timetable t ON r.id = t.room_id
            GROUP BY r.id
        """).fetchall()

        c = canvas.Canvas(filename, pagesize=letter)
        c.drawString(100, 750, "Statistiques d'occupation des salles")

        y = 700
        for row in stats:
            c.drawString(100, y, f"{row['name']} : {row['nb_creneaux']} créneaux")
            y -= 20

        c.save()
        conn.close()
        print(f" Statistiques exportées vers {filename}")

    # --- CORRECTION: Method inside the class (4 spaces indentation) ---
    def generer_planning_complet(self):
        """
        Génère l'emploi du temps complet en utilisant l'algorithme génétique.
        Cette action efface le planning existant pour une régénération propre.
        """
        print("Démarrage de la génération automatique...")
        
        # 1. Nettoyer la table timetable (Optionnel: on pourrait vouloir garder les trucs manuels)
        conn = getConnection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM timetable") # Reset complet pour la démo
        conn.commit()
        conn.close()
        
        # 2. Lancer l'algo
        from Schedule import GeneticAlgorithm, Configuration, DAY_HOURS
        
        # Recharger la config pour être sûr d'avoir les dernières données
        config = Configuration.get_instance()
        config.load_data()
        
        if config.GetNumberOfCourseClasses() == 0:
            return "Aucun cours à planifier (Tables vides ?)"
            
        ga = GeneticAlgorithm(population_size=12, mutation_size=2)
        # On lance sur 50 générations (peut être ajusté)
        best_schedule = ga.evolve(max_generations=50, target_fitness=0.95)
        
        # 3. Sauvegarder le meilleur résultat
        conn = getConnection()
        cursor = conn.cursor()
        
        count = 0
        nr = config.GetNumberOfRooms()
        day_size = DAY_HOURS * nr
        
        for cc, pos in best_schedule.classes.items():
            # Décodage de la position
            day = pos // day_size
            rem = pos % day_size
            room_idx = rem // DAY_HOURS
            time = rem % DAY_HOURS
            
            # Récupération des IDs réels
            # Note: day est 0-indexed dans l'algo, mais 1-indexed dans la DB (Lundi=1)
            db_day = day + 1 
            
            # Ajustement de l'heure (L'algo commence à 0 -> 8h00)
            db_start_hour = 8 + time
            
            # Récupération de l'objet Salle réel
            room_wrapper = config.GetRoomById(room_idx)
            room_id = room_wrapper.GetId()
            
            # Données du cours
            subj = cc.GetSubject()
            grp = cc.GetGroups()[0] # On a simplifié à 1 groupe
            instr = cc.GetProfessor()
            duration = cc.GetDuration()
            
            # Insertion directe (on bypass check_conflict car l'algo l'a fait)
            try:
                cursor.execute("""
                    INSERT INTO timetable (course_id, instructor_id, group_id, room_id, day, start_hour, duration, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (subj['id'], instr['id'], grp['id'], room_id, db_day, db_start_hour, duration, self.admin_id))
                count += 1
            except Exception as e:
                print(f"Erreur insertion {subj['name']}: {e}")
                
        conn.commit()
        conn.close()
        
        return f"Génération terminée ! {count} cours planifiés avec un score de {best_schedule.fitness:.2%}."

    def affecter_automatiquement(self, subject_id, group_id, day, start_hour, duration):
        conn = getConnection()
        cursor = conn.cursor()

        # 1. Get Group info (student count)
        cursor.execute("SELECT student_count FROM groups WHERE id = ?", (group_id,))
        group = cursor.fetchone()
        if not group:
            conn.close()
            return "Group not found."

        # 2. Get Subject info (required equipment)
        cursor.execute("SELECT required_equipment FROM subjects WHERE id = ?", (subject_id,))
        subject = cursor.fetchone()
        
        # 3. Get all active rooms
        cursor.execute("SELECT * FROM rooms WHERE active = 1 ORDER BY capacity ASC")
        all_rooms = cursor.fetchall()

        # 4. Search for an available room
        assigned_room_id = None
        room_name = None
        for room in all_rooms:
            # Check capacity constraint
            if room['capacity'] < group['student_count']:
                continue
                
            # Check equipment constraint
            if subject['required_equipment']:
                if not room['equipments'] or subject['required_equipment'] not in room['equipments']:
                    continue

            # Check for schedule conflicts (Room availability)
            conflict = check_conflict(0, group_id, room['id'], day, start_hour, duration)
            
            if not conflict:
                assigned_room_id = room['id']
                room_name = room['name']
                break

        if assigned_room_id:
            # Find an available instructor
            cursor.execute("SELECT instructor_id FROM subject_instructors WHERE subject_id = ? LIMIT 1", (subject_id,))
            instr = cursor.fetchone()
            
            if instr:
                success = self.creer_creneau(subject_id, instr['instructor_id'], group_id, 
                                             assigned_room_id, day, start_hour, duration)
                conn.close()
                if success:
                    return f"Success: Room {room_name} assigned automatically."
            else:
                conn.close()
                return "Error: No qualified instructor found for this subject."
        
        conn.close()
        return "Error: No suitable room found for this slot."
