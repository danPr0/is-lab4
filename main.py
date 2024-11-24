import csv
import copy
import random


class ScheduleCSP:
    def __init__(self, groups_file, teachers_file, subjects_file, rooms_file):
        self.groups = self.read_csv(groups_file)
        self.teachers = self.read_csv(teachers_file)
        self.subjects = self.read_csv(subjects_file)
        self.rooms = self.read_csv(rooms_file)
        self.schedule = []

        self.slots = [f"Day{i}_Slot{j}" for i in range(1, 6) for j in range(1, 5)]
        self.domains = self.init_domains()

        self.best_assignment = None
        self.best_quality = - float('inf')
        self.steps = 0

    def read_csv(self, file):
        with open(file, 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))

    def save_best_assignment(self, filename='output/schedule.csv'):
        keys = self.best_assignment[0].keys()
        with open(filename, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.best_assignment)

    def init_domains(self):
        domains = {}
        for subject in self.subjects:
            for hour in range(int(subject['hours'])):
                domains[(subject['group'], subject['subject'], hour + 1)] = {
                    "slots": self.slots,
                    "rooms": [room['room'] for room in self.rooms],
                    "teachers": [
                        lec['teacher'] for lec in self.teachers if subject['subject'] in lec['subjects']
                    ]
                }
        return domains

    def is_consistent(self, assignment, group, slot, room, teacher):
        for other in assignment:
            if (other['slot'] == slot
                    and (other['group'] == group or other['room'] == room or other['teacher'] == teacher)):
                return False
        return True

    def calculate_quality(self, assignment):
        windows_penalty = 0
        room_size_penalty = 0
        teacher_inter_penalty = 0

        schedules = {"teachers": {}, "groups": {}}
        for entry in assignment:
            teacher = entry['teacher']
            group = entry['group']
            slot = entry['slot']

            schedules["teachers"].setdefault(teacher, []).append(slot)
            schedules["groups"].setdefault(group, []).append(slot)

        for entity, schedule in schedules.items():
            for _, slots in schedule.items():
                slots = sorted(slots)
                for i in range(1, len(slots)):
                    prev_day, prev_slot = map(lambda x: int(x[-1:]), slots[i - 1].split('_'))
                    curr_day, curr_slot = map(lambda x: int(x[-1:]), slots[i].split('_'))
                    if curr_day == prev_day and curr_slot > prev_slot + 1:
                        windows_penalty += 1

        for entry in assignment:
            group_size = next(int(group['num_students']) for group in self.groups if group['name'] == entry['group'])
            room_capacity = next(int(room['capacity']) for room in self.rooms if room['room'] == entry['room'])
            if group_size > room_capacity:
                room_size_penalty += 1

            teacher_subjects = next(filter(lambda x: x['teacher'] == entry['teacher'], self.teachers))['subjects'].split(';')
            if entry['subject'] not in teacher_subjects:
                teacher_inter_penalty += 1

        total_penalty = windows_penalty + room_size_penalty + teacher_inter_penalty
        return - total_penalty

    def backtrack(self, domains, assignment=[]):
        if len(assignment) == len(self.domains):
            if self.best_quality != 0:
                self.steps += 1
            quality_result = self.calculate_quality(assignment)
            if quality_result > self.best_quality:
                self.best_assignment = copy.deepcopy(assignment)
                self.best_quality = quality_result
            return

        # var = list(domains.keys())[random.randint(0, len(domains) - 1)]
        var = self.select_variable_mrv(domains, assignment)
        domain = domains.pop(var)

        ordered_slots = self.least_constraining_value(domain, domains, assignment)
        for slot in ordered_slots:
            for room in domain['rooms']:
                for teacher in domain['teachers']:
                    if self.is_consistent(assignment, var[0], slot, room, teacher):
                        # self.steps += 1
                        assignment.append({
                            "group": var[0],
                            "subject": var[1],
                            "slot": slot,
                            "room": room,
                            "teacher": teacher
                        })
                        quality = self.calculate_quality(assignment)
                        if quality > self.best_quality:
                            self.backtrack(copy.deepcopy(domains), assignment)
                        assignment.pop()

    def select_variable_mrv(self, domains, assignment):

        min_domain_size = float('inf')
        selected_var = None

        for var in domains.keys():
            domain_size = self.count_available_domains(var, domains[var], assignment)
            # domain_size = len(domains[var]['slots']) * len(domains[var]['rooms']) * len(domains[var]['teachers'])
            # domain_size = len(domains[var]['slots'])
            if domain_size != 0 and domain_size < min_domain_size:
                min_domain_size = domain_size
                selected_var = var

        return selected_var

    def count_available_domains(self, var, domain, assignment):
        result = 0
        for slot in domain['slots']:
            for room in domain['rooms']:
                for teacher in domain['teachers']:
                    result += self.is_consistent(assignment, var[0], slot, room, teacher)
        return result

    def get_available_slots(self, var, domain, assignment):
        result = []
        for slot in domain['slots']:
            found = False
            for room in domain['rooms']:
                for teacher in domain['teachers']:
                    if self.is_consistent(assignment, var[0], slot, room, teacher):
                        found = True
            if found:
                result.append(slot)
        return result

    def least_constraining_value(self, domain, domains, assignment):
        value_constraints = []

        for slot in domain['slots']:
            count = 0
            for other_var, other_domain in domains.items():
                if any(a['group'] == other_var for a in assignment):
                    continue
                if slot in other_domain['slots']:
                    count += 1
            value_constraints.append((slot, count))

        value_constraints.sort(key=lambda x: x[1])
        return [vc[0] for vc in value_constraints]


csp = ScheduleCSP("data/groups.csv", "data/teachers.csv", "data/subjects.csv", "data/rooms.csv")
csp.backtrack(copy.deepcopy(csp.domains))
csp.save_best_assignment()
print('Best quality: {}'.format(csp.best_quality))
print('Steps: {}'.format(csp.steps))
