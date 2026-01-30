"""
Contrôleur pour les fonctionnalités enseignants
"""

import sqlite3
from datetime import datetime
from database import getConnection

# Jours de la semaine (copié de database.py pour éviter l'import circulaire)
DAYS = {1: "Lundi", 2: "Mardi", 3: "Mercredi", 4: "Jeudi", 5: "Vendredi"}

class TeacherController:
    def __init__(self, user_id):
        """
        Initialise le contrôleur avec l'ID de l'utilisateur enseignant
        """
        self.user_id = user_id
        self.instructor_id = self._get_instructor_id()
    
    def _get_instructor_id(self):
        """Récupère l'ID de l'instructeur"""
        conn = getConnection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM instructors WHERE user_id = ?", (self.user_id,))
        result = cursor.fetchone()
        conn.close()
        return result['id'] if result else None
    
    def get_teacher_timetable(self):
        """
        CONSULTER SON EMPLOI DU TEMPS
        Retourne l'emploi du temps personnalisé de l'enseignant
        """
        if not self.instructor_id:
            return {"success": False, "error": "Enseignant non trouvé"}
        
        conn = getConnection()
        cursor = conn.cursor()
        
        query = """
        SELECT 
            t.day,
            t.start_hour,
            t.duration,
            s.name AS subject_name,
            s.code AS subject_code,
            g.name AS group_name,
            r.name AS room_name,
            r.type AS room_type
        FROM timetable t
        JOIN subjects s ON t.course_id = s.id
        JOIN groups g ON t.group_id = g.id
        JOIN rooms r ON t.room_id = r.id
        WHERE t.instructor_id = ?
        ORDER BY t.day, t.start_hour
        """
        
        cursor.execute(query, (self.instructor_id,))
        timetable_slots = cursor.fetchall()
        conn.close()
        
        # Organiser par jour
        organized_timetable = {}
        for day_num, day_name in DAYS.items():
            organized_timetable[day_name] = []
        
        for slot in timetable_slots:
            day_name = DAYS.get(slot['day'], 'Inconnu')
            end_hour = slot['start_hour'] + slot['duration']
            slot_info = {
                'jour': day_name,
                'heure': f"{slot['start_hour']:02d}h-{end_hour:02d}h",
                'matiere': slot['subject_name'],
                'code': slot['subject_code'],
                'groupe': slot['group_name'],
                'salle': slot['room_name'],
                'type_salle': slot['room_type']
            }
            organized_timetable[day_name].append(slot_info)
        
        return {"success": True, "timetable": organized_timetable}
    
    # MODIFICATION: Cette méthode prend maintenant des noms au lieu d'IDs
    def submit_reservation(self, room_name, group_name, day, start_hour, duration, reason=""):
        """
        SOUMETTRE UNE RÉSERVATION PONCTUELLE
        Demande de réservation de salle pour séance de rattrapage, réunion, etc.
        """
        # Validation basique
        if day < 1 or day > 5:
            return {"success": False, "message": "Jour invalide (1-5)"}
        if start_hour < 8 or start_hour > 18:
            return {"success": False, "message": "Heure invalide (8-18h)"}
        if duration < 1 or duration > 4:
            return {"success": False, "message": "Durée invalide (1-4h)"}
        
        if not self.instructor_id:
            return {"success": False, "message": "Enseignant non trouvé"}
        
        conn = getConnection()
        cursor = conn.cursor()
        
        # Récupérer l'ID de la salle par son nom
        cursor.execute("SELECT id FROM rooms WHERE name = ? AND active = 1", (room_name,))
        room = cursor.fetchone()
        if not room:
            conn.close()
            return {"success": False, "message": f"Salle '{room_name}' non trouvée"}
        room_id = room['id']
        
        # Récupérer l'ID du groupe par son nom
        cursor.execute("SELECT id FROM groups WHERE name = ? AND active = 1", (group_name,))
        group = cursor.fetchone()
        if not group:
            conn.close()
            return {"success": False, "message": f"Groupe '{group_name}' non trouvé"}
        group_id = group['id']
        
        # Vérifier si la salle est disponible
        conflict = self._check_room_availability(room_id, day, start_hour, duration)
        if conflict:
            conn.close()
            return {"success": False, "message": conflict}
        
        try:
            cursor.execute("""
                INSERT INTO reservations 
                (instructor_id, room_id, group_id, day, start_hour, duration, reason, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
            """, (self.instructor_id, room_id, group_id, day, start_hour, duration, reason))
            
            conn.commit()
            reservation_id = cursor.lastrowid
            conn.close()
            
            return {
                "success": True, 
                "message": f"Demande de réservation soumise avec succès (ID: {reservation_id})",
                "reservation_id": reservation_id
            }
        except sqlite3.IntegrityError as e:
            conn.close()
            return {"success": False, "message": f"Erreur: {str(e)}"}
    
    def _check_room_availability(self, room_id, day, start_hour, duration):
        """Vérifie si une salle est disponible à un créneau donné"""
        conn = getConnection()
        cursor = conn.cursor()
        end_hour = start_hour + duration
        
        # Vérifier dans l'emploi du temps
        cursor.execute("""
            SELECT id FROM timetable 
            WHERE room_id = ? AND day = ? 
            AND (start_hour < ?) AND (? < start_hour + duration)
        """, (room_id, day, end_hour, start_hour))
        
        if cursor.fetchone():
            conn.close()
            return "Salle déjà occupée dans l'emploi du temps"
        
        # Vérifier dans les réservations approuvées
        cursor.execute("""
            SELECT id FROM reservations 
            WHERE room_id = ? AND day = ? AND status = 'APPROVED'
            AND (start_hour < ?) AND (? < start_hour + duration)
        """, (room_id, day, end_hour, start_hour))
        
        if cursor.fetchone():
            conn.close()
            return "Salle déjà réservée à ce créneau"
        
        conn.close()
        return None
    
    def declare_unavailability(self, day, start_hour, duration, reason=""):
        """
        DÉCLARER UNE INDISPONIBILITÉ
        L'enseignant signale qu'il n'est pas disponible à un créneau
        """
        # Validation
        if day < 1 or day > 5:
            return {"success": False, "message": "Jour invalide (1-5)"}
        if start_hour < 8 or start_hour > 18:
            return {"success": False, "message": "Heure invalide (8-18h)"}
        
        if not self.instructor_id:
            return {"success": False, "message": "Enseignant non trouvé"}
        
        conn = getConnection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO teacher_unavailability 
                (instructor_id, day, start_hour, duration, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (self.instructor_id, day, start_hour, duration, reason))
            
            conn.commit()
            conn.close()
            
            # Mettre à jour les indisponibilités dans la table instructors
            self._update_unavailable_slots()
            
            return {"success": True, "message": "Indisponibilité déclarée avec succès"}
        except Exception as e:
            conn.close()
            return {"success": False, "message": f"Erreur: {str(e)}"}
    
    def _update_unavailable_slots(self):
        """Met à jour le champ unavailable_slots dans instructors"""
        conn = getConnection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT day, start_hour, duration 
            FROM teacher_unavailability 
            WHERE instructor_id = ?
        """, (self.instructor_id,))
        
        slots = cursor.fetchall()
        
        # Formater les créneaux
        formatted = []
        for slot in slots:
            day_name = DAYS.get(slot['day'], f"Jour{slot['day']}")
            start = slot['start_hour']
            end = start + slot['duration']
            formatted.append(f"{day_name}_{start:02d}-{end:02d}")
        
        # Mettre à jour
        cursor.execute("""
            UPDATE instructors 
            SET unavailable_slots = ?
            WHERE id = ?
        """, (','.join(formatted), self.instructor_id))
        
        conn.commit()
        conn.close()
    
    def search_available_room(self, day, start_hour, duration=2, min_capacity=30):
        """
        RECHERCHER UNE SALLE VACANTE
        Recherche selon critères (horaire, capacité, équipement)
        """
        # Validation
        if day < 1 or day > 5:
            return {"success": False, "message": "Jour invalide", "rooms": []}
        
        conn = getConnection()
        cursor = conn.cursor()
        end_hour = start_hour + duration
        
        query = """
        SELECT r.* FROM rooms r
        WHERE r.active = 1 
        AND r.capacity >= ?
        AND r.id NOT IN (
            SELECT room_id FROM timetable 
            WHERE day = ? 
            AND (start_hour < ?) AND (? < start_hour + duration)
            UNION
            SELECT room_id FROM reservations 
            WHERE day = ? AND status = 'APPROVED'
            AND (start_hour < ?) AND (? < start_hour + duration)
        )
        ORDER BY r.name
        """
        
        params = [min_capacity, day, end_hour, start_hour, day, end_hour, start_hour]
        cursor.execute(query, params)
        rooms = cursor.fetchall()
        conn.close()
        
        # Formater les résultats
        rooms_list = []
        for room in rooms:
            rooms_list.append({
                'nom': room['name'],
                'type': room['type'],
                'capacité': room['capacity'],
                'équipements': room['equipments'],
                'disponible': True
            })
        
        return {"success": True, "rooms": rooms_list, "count": len(rooms_list)}
    
    def get_reservation_status(self):
        """Voir le statut des réservations soumises"""
        if not self.instructor_id:
            return {"success": False, "reservations": []}
        
        conn = getConnection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                r.id, r.day, r.start_hour, r.duration,
                ro.name AS salle, r.reason, r.status,
                r.created_at AS date_soumission
            FROM reservations r
            LEFT JOIN rooms ro ON r.room_id = ro.id
            WHERE r.instructor_id = ?
            ORDER BY r.created_at DESC
        """, (self.instructor_id,))
        
        reservations = cursor.fetchall()
        conn.close()
        
        # Formater
        formatted = []
        for res in reservations:
            day_name = DAYS.get(res['day'], f"Jour{res['day']}")
            end_hour = res['start_hour'] + res['duration']
            formatted.append({
                'id': res['id'],
                'jour': day_name,
                'horaire': f"{res['start_hour']}h-{end_hour}h",
                'salle': res['salle'],
                'motif': res['reason'],
                'statut': res['status'],
                'soumis_le': res['date_soumission']
            })
        
        return {"success": True, "reservations": formatted}