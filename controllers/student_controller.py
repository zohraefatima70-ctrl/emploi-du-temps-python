"""
Contrôleur pour les fonctionnalités étudiants
"""

from datetime import datetime
from database import getConnection

# Jours de la semaine
DAYS = {1: "Lundi", 2: "Mardi", 3: "Mercredi", 4: "Jeudi", 5: "Vendredi"}

class StudentController:
    def __init__(self, user_id):
        """
        Initialise le contrôleur avec l'ID de l'utilisateur étudiant
        """
        self.user_id = user_id
        self.group_id = self._get_student_group()
    
    def _get_student_group(self):
        """
        Trouve le groupe de l'étudiant via la table student_groups.
        
        Returns:
            int or None: ID du groupe ou None si non trouvé
        """
        conn = getConnection()
        cursor = conn.cursor()
        
        # Récupérer le groupe de l'étudiant via la table de liaison
        cursor.execute("""
            SELECT g.id 
            FROM groups g
            JOIN student_groups sg ON g.id = sg.group_id
            WHERE sg.user_id = ? AND g.active = 1
            LIMIT 1
        """, (self.user_id,))
        
        result = cursor.fetchone()
        
        # Fallback: si pas dans student_groups, prendre le premier groupe actif
        if not result:
            cursor.execute("SELECT id FROM groups WHERE active = 1 LIMIT 1")
            result = cursor.fetchone()
        
        conn.close()
        return result['id'] if result else None
    
    def get_group_timetable(self):
        """
        CONSULTER L'EMPLOI DU TEMPS DE SON GROUPE
        Retourne l'emploi du temps complet du groupe
        """
        if not self.group_id:
            return {"success": False, "error": "Groupe non trouvé pour cet étudiant"}
        
        conn = getConnection()
        cursor = conn.cursor()
        
        # Récupérer le nom du groupe
        cursor.execute("SELECT name FROM groups WHERE id = ?", (self.group_id,))
        group = cursor.fetchone()
        group_name = group['name'] if group else "Inconnu"
        
        # Récupérer l'emploi du temps
        query = """
        SELECT 
            t.day,
            t.start_hour,
            t.duration,
            s.name AS subject_name,
            s.code AS subject_code,
            s.type AS subject_type,
            i.name AS instructor_name,
            r.name AS room_name,
            r.type AS room_type
        FROM timetable t
        JOIN subjects s ON t.course_id = s.id
        JOIN instructors i ON t.instructor_id = i.id
        JOIN rooms r ON t.room_id = r.id
        WHERE t.group_id = ?
        ORDER BY t.day, t.start_hour
        """
        
        cursor.execute(query, (self.group_id,))
        timetable_slots = cursor.fetchall()
        conn.close()
        
        # Organiser par jour
        organized = {}
        for day_num, day_name in DAYS.items():
            organized[day_name] = []
        
        for slot in timetable_slots:
            day_name = DAYS.get(slot['day'], 'Inconnu')
            end_hour = slot['start_hour'] + slot['duration']
            slot_info = {
                'jour': day_name,
                'horaire': f"{slot['start_hour']:02d}h-{end_hour:02d}h",
                'matiere': slot['subject_name'],
                'code': slot['subject_code'],
                'type': slot['subject_type'],
                'enseignant': slot['instructor_name'],
                'salle': slot['room_name'],
                'type_salle': slot['room_type']
            }
            organized[day_name].append(slot_info)
        
        return {
            "success": True, 
            "groupe": group_name,
            "emploi_du_temps": organized
        }
    
    def search_free_room(self, day=None, start_hour=None, duration=2):
        """
        RECHERCHER UNE SALLE LIBRE
        Pour travaux de groupe, révisions, etc.
        
        Si jour et heure spécifiés: cherche les salles libres à ce créneau
        Si seulement jour spécifié: montre toutes les salles avec leurs disponibilités
        Si rien spécifié: liste toutes les salles
        """
        conn = getConnection()
        cursor = conn.cursor()
        
        if day and start_hour:
            # Recherche précise pour un créneau
            end_hour = start_hour + duration
            query = """
            SELECT r.name, r.type, r.capacity FROM rooms r
            WHERE r.active = 1 
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
            
            cursor.execute(query, (day, end_hour, start_hour, day, end_hour, start_hour))
            rooms = cursor.fetchall()
            conn.close()
            
            # MODIFICATION: Retourner des noms au lieu d'IDs
            rooms_list = []
            for room in rooms:
                rooms_list.append({
                    'nom': room['name'],
                    'type': room['type'],
                    'capacité': room['capacity'],
                    'horaire': f"{start_hour}h-{end_hour}h"
                })
            
            return {"success": True, "rooms": rooms_list}
        
        elif day:
            # Voir les disponibilités sur toute la journée
            cursor.execute("SELECT * FROM rooms WHERE active = 1 ORDER BY name")
            all_rooms = cursor.fetchall()
            
            rooms_with_schedule = []
            for room in all_rooms:
                # Récupérer les créneaux occupés
                cursor.execute("""
                    SELECT start_hour, duration 
                    FROM timetable 
                    WHERE room_id = ? AND day = ?
                    UNION
                    SELECT start_hour, duration 
                    FROM reservations 
                    WHERE room_id = ? AND day = ? AND status = 'APPROVED'
                    ORDER BY start_hour
                """, (room['id'], day, room['id'], day))
                
                occupied = cursor.fetchall()
                
                # Calculer les créneaux libres (8h-18h)
                free_slots = []
                current = 8  # Début de journée
                
                for slot in occupied:
                    slot_start = slot['start_hour']
                    slot_end = slot_start + slot['duration']
                    
                    if current < slot_start:
                        free_slots.append(f"{current}h-{slot_start}h")
                    
                    current = max(current, slot_end)
                
                if current < 18:
                    free_slots.append(f"{current}h-18h")
                
                rooms_with_schedule.append({
                    'nom': room['name'],
                    'type': room['type'],
                    'capacité': room['capacity'],
                    'creneaux_libres': free_slots
                })
            
            conn.close()
            return {"success": True, "rooms": rooms_with_schedule}
        
        else:
            # Lister toutes les salles (retourner des noms)
            cursor.execute("SELECT name, type, capacity, equipments FROM rooms WHERE active = 1 ORDER BY name")
            rooms = cursor.fetchall()
            conn.close()
            
            rooms_list = []
            for room in rooms:
                rooms_list.append({
                    'nom': room['name'],
                    'type': room['type'],
                    'capacité': room['capacity'],
                    'équipements': room['equipments'] or "Aucun"
                })
            
            return {"success": True, "rooms": rooms_list}
    
    def get_today_schedule(self):
        """
        VOIR L'EMPLOI DU TEMPS D'AUJOURD'HUI
        Version simplifiée pour consultation rapide
        """
        if not self.group_id:
            return {"success": False, "error": "Groupe non trouvé"}
        
        # Jour actuel (1=Lundi, 5=Vendredi)
        today = datetime.now().weekday() + 1
        
        conn = getConnection()
        cursor = conn.cursor()
        
        query = """
        SELECT 
            t.start_hour,
            t.duration,
            s.name AS subject_name,
            i.name AS instructor_name,
            r.name AS room_name
        FROM timetable t
        JOIN subjects s ON t.course_id = s.id
        JOIN instructors i ON t.instructor_id = i.id
        JOIN rooms r ON t.room_id = r.id
        WHERE t.group_id = ? AND t.day = ?
        ORDER BY t.start_hour
        """
        
        cursor.execute(query, (self.group_id, today))
        today_schedule = cursor.fetchall()
        conn.close()
        
        schedule_list = []
        for slot in today_schedule:
            end_hour = slot['start_hour'] + slot['duration']
            schedule_list.append({
                'horaire': f"{slot['start_hour']:02d}h-{end_hour:02d}h",
                'matiere': slot['subject_name'],
                'enseignant': slot['instructor_name'],
                'salle': slot['room_name']
            })
        
        return {
            "success": True,
            "jour": DAYS.get(today, "Aujourd'hui"),
            "cours": schedule_list,
            "nombre_cours": len(schedule_list)
        }