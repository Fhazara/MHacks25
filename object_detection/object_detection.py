def process_violations(data):
    # Placeholder for postprocessing
    print("Collected violation data:")
    for entry in data:
        print(entry)

def merge_reports(data):
    if not data:
        return []
    def normalize_violations(violations):
        norm = []
        for v in violations:
            missing = v.get("missing", {})
            if isinstance(missing, dict):
                missing_norm = dict(sorted(missing.items()))
            else:
                missing_norm = {}
                for item in missing:
                    missing_norm[item] = missing_norm.get(item, 0) + 1
            norm.append({**v, "missing": missing_norm})
        return norm

    merged = []
    current = {
        "frame_start": data[0]["frame_start"],
        "frame_end": data[0]["frame_end"],
        "state": data[0]["state"],
        "violations": normalize_violations(data[0]["violations"]),
        "persons": data[0]["persons"]
    }
    for entry in data[1:]:
        same_state = entry["state"] == current["state"]
        entry_violations = normalize_violations(entry["violations"])
        same_violations = entry_violations == current["violations"]
        same_persons = entry["persons"] == current["persons"]
        # Merge if ranges are consecutive and all else matches
        if same_state and same_violations and same_persons and entry["frame_start"] == current["frame_end"] + 1:
            current["frame_end"] = entry["frame_end"]
        else:
            merged.append(current.copy())
            current = {
                "frame_start": entry["frame_start"],
                "frame_end": entry["frame_end"],
                "state": entry["state"],
                "violations": entry_violations,
                "persons": entry["persons"]
            }
    merged.append(current)
    return merged

# Script to capture video from MacBook camera, run YOLO object detection, and display results
import cv2
from ultralytics import YOLO

def main():
    # Track positive equipment sightings
    equipment_types = {"safety vest", "hardhat", "mask"}
    equipment_seen = set()
    equipment_count = 0
    equipment_log = []
    # Load YOLO model
    model = YOLO('models/best_yolo11m.pt')
    #model = YOLO('models/best_our.pt')


    # Open webcam (0 is usually the default camera)
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    frame_id = 0
    violation_data = []
    MIN_FRAMES = 10  # Minimum duration for a violation to be logged (in frames)
    # State machine variables
    state = "waiting"  # can be 'waiting', 'confirming', 'confirmed'
    candidate_violation = None
    candidate_start = None
    confirmed_violation = None
    confirmed_start = None
    confirmed_end = None

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break

        results = model(frame)
        person_count = 0
        no_flags = []
        positive_flags = set()

        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls[0])
                label = model.names[cls] if hasattr(model, 'names') else str(cls)
                label_lower = label.lower()
                if label_lower == "person":
                    person_count += 1
                elif label_lower in equipment_types:
                    positive_flags.add(label_lower)
                elif label_lower.startswith("no-"):
                    no_flags.append(label_lower[3:])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f'{label} {conf:.2f}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Update equipment sightings only if new equipment is detected
        new_equipment = positive_flags - equipment_seen
        if new_equipment:
            equipment_seen.update(new_equipment)
            equipment_count = len(equipment_seen)
            equipment_log.append({
                "frame_id": frame_id,
                "new_equipment": list(new_equipment),
                "total_equipment": equipment_count
            })

        # State machine for violation tracking
        current_violation = None
        if person_count > 0 and no_flags:
            current_violation = {
                "state": "Michigan",
                "violations": [
                    {"missing": sorted(no_flags)}
                ],
                "persons": person_count
            }

        if state == "waiting":
            if current_violation:
                state = "confirming"
                candidate_violation = current_violation
                candidate_start = frame_id
        elif state == "confirming":
            if current_violation == candidate_violation:
                # Still confirming
                if frame_id - candidate_start + 1 >= MIN_FRAMES:
                    # Confirmed
                    state = "confirmed"
                    confirmed_violation = candidate_violation
                    confirmed_start = candidate_start
                    confirmed_end = frame_id
            else:
                # Violation changed before confirmation
                state = "waiting"
                candidate_violation = None
                candidate_start = None
        elif state == "confirmed":
            if current_violation == confirmed_violation:
                # Extend confirmed violation
                confirmed_end = frame_id
            else:
                # Violation ended or changed, log it with full range
                if confirmed_end - confirmed_start + 1 >= MIN_FRAMES:
                    violation_data.append({
                        "frame_start": confirmed_start,
                        "frame_end": confirmed_end,
                        "state": confirmed_violation["state"],
                        "violations": confirmed_violation["violations"],
                        "persons": confirmed_violation["persons"]
                    })
                state = "waiting"
                candidate_violation = None
                candidate_start = None
                confirmed_violation = None
                confirmed_start = None
                confirmed_end = None

        cv2.imshow('YOLO Detection', frame)
        frame_id += 1
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    # Handle last confirmed violation at end
    if state == "confirmed" and confirmed_violation is not None:
        if confirmed_end - confirmed_start + 1 >= MIN_FRAMES:
            violation_data.append({
                "frame_start": confirmed_start,
                "frame_end": confirmed_end,
                "state": confirmed_violation["state"],
                "violations": confirmed_violation["violations"],
                "persons": confirmed_violation["persons"]
            })
    merged = merge_reports(violation_data)
    process_violations(merged)
    print("Equipment sightings log:")
    for entry in equipment_log:
        print(entry)

    with open("sample_batches.txt", "w") as f:
        for item in sample_batches:
            f.write(str(item) + "\n")

#    from agent_connector import send_report_to_agentverse

if __name__ == "__main__":
    main()
