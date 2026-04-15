import json
import logging
import os
from pathlib import Path

import cv2
from ultralytics import YOLO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.resolve()

# ── Configuration via environment variables ───────────────────────────────────
CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", "1"))
MODEL_PATH = os.environ.get("MODEL_PATH", str(BASE_DIR / "models" / "best_yolo11m.pt"))
SAMPLE_BATCHES_FILE = BASE_DIR / "sample_batches.txt"
MIN_FRAMES = int(os.environ.get("MIN_FRAMES", "10"))


def process_violations(data: list) -> None:
    logger.info("Collected %d violation record(s)", len(data))
    for entry in data:
        logger.debug("Violation entry: %s", entry)


def merge_reports(data: list) -> list:
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
        "persons": data[0]["persons"],
    }
    for entry in data[1:]:
        same_state = entry["state"] == current["state"]
        entry_violations = normalize_violations(entry["violations"])
        same_violations = entry_violations == current["violations"]
        same_persons = entry["persons"] == current["persons"]
        if (
            same_state
            and same_violations
            and same_persons
            and entry["frame_start"] == current["frame_end"] + 1
        ):
            current["frame_end"] = entry["frame_end"]
        else:
            merged.append(current.copy())
            current = {
                "frame_start": entry["frame_start"],
                "frame_end": entry["frame_end"],
                "state": entry["state"],
                "violations": entry_violations,
                "persons": entry["persons"],
            }
    merged.append(current)
    return merged


def main() -> None:
    equipment_types = {"safety vest", "hardhat", "mask"}
    equipment_seen: set = set()
    equipment_count = 0
    equipment_log = []

    model = YOLO(MODEL_PATH)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        logger.error("Could not open camera at index %d", CAMERA_INDEX)
        return

    frame_id = 0
    violation_data = []

    # State machine variables
    state = "waiting"
    candidate_violation = None
    candidate_start = None
    confirmed_violation = None
    confirmed_start = None
    confirmed_end = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.error("Failed to capture frame from camera %d", CAMERA_INDEX)
                break

            results = model(frame, verbose=False)
            person_count = 0
            no_flags = []
            positive_flags: set = set()

            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    label = model.names[cls] if hasattr(model, "names") else str(cls)
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
                    cv2.putText(
                        frame,
                        f"{label} {conf:.2f}",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )

            new_equipment = positive_flags - equipment_seen
            if new_equipment:
                equipment_seen.update(new_equipment)
                equipment_count = len(equipment_seen)
                equipment_log.append({
                    "frame_id": frame_id,
                    "new_equipment": list(new_equipment),
                    "total_equipment": equipment_count,
                })

            current_violation = None
            if person_count > 0 and no_flags:
                current_violation = {
                    "state": "Michigan",
                    "violations": [{"missing": sorted(no_flags)}],
                    "persons": person_count,
                }

            if state == "waiting":
                if current_violation:
                    state = "confirming"
                    candidate_violation = current_violation
                    candidate_start = frame_id
            elif state == "confirming":
                if current_violation == candidate_violation:
                    if frame_id - candidate_start + 1 >= MIN_FRAMES:
                        state = "confirmed"
                        confirmed_violation = candidate_violation
                        confirmed_start = candidate_start
                        confirmed_end = frame_id
                else:
                    state = "waiting"
                    candidate_violation = None
                    candidate_start = None
            elif state == "confirmed":
                if current_violation == confirmed_violation:
                    confirmed_end = frame_id
                else:
                    if confirmed_end - confirmed_start + 1 >= MIN_FRAMES:
                        violation_data.append({
                            "frame_start": confirmed_start,
                            "frame_end": confirmed_end,
                            "state": confirmed_violation["state"],
                            "violations": confirmed_violation["violations"],
                            "persons": confirmed_violation["persons"],
                        })
                    state = "waiting"
                    candidate_violation = None
                    candidate_start = None
                    confirmed_violation = None
                    confirmed_start = None
                    confirmed_end = None

            cv2.imshow("YOLO Detection", frame)
            frame_id += 1
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    # Flush last confirmed violation
    if state == "confirmed" and confirmed_violation is not None:
        if confirmed_end - confirmed_start + 1 >= MIN_FRAMES:
            violation_data.append({
                "frame_start": confirmed_start,
                "frame_end": confirmed_end,
                "state": confirmed_violation["state"],
                "violations": confirmed_violation["violations"],
                "persons": confirmed_violation["persons"],
            })

    merged = merge_reports(violation_data)
    process_violations(merged)

    logger.info("Equipment sightings log (%d entries)", len(equipment_log))
    for entry in equipment_log:
        logger.debug("Equipment sighting: %s", entry)

    # Write merged batches as JSON Lines (one object per line)
    with open(SAMPLE_BATCHES_FILE, "w", encoding="utf-8") as fh:
        for item in merged:
            fh.write(json.dumps(item) + "\n")
    logger.info("Wrote %d batch(es) to %s", len(merged), SAMPLE_BATCHES_FILE)


if __name__ == "__main__":
    main()
