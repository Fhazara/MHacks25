# mhack25
# Construction Safety Equipment Monitoring

## Inspiration  
We were fascinated by the possibility of deploying large AI models on **edge devices** using **MemryX acceleration**. Our idea was to port a fine-tuned object detection model into MemryX format to enhance **safety monitoring on construction sites**. The goal: gather high-objectivity data on personal protective equipment (PPE) usage with minimal compute resources.  

Once collected over time, this data could be analyzed to understand missing equipment patterns and determine if any safety laws were broken — with the help of **AI agents** acting as relays and law experts.

---

## What It Does  
Our prototype leverages a fine-tuned **YOLO11** object detection model to monitor live video streams:  
- Detects PPE-related classes (e.g., helmets, vests, masks).  
- Applies postprocessing to **draw bounding boxes** on detected objects.  
- Logs cases of missing safety equipment (e.g., `"NO-hardhat"`).  
- Uses a state-machine approach to minimize redundant logs.  
- At the end of a monitoring session, reports are bundled and sent via **HTTP** to AI agents.  
- These agents analyze the reports, identify potential legal violations, and send warnings to managers or stakeholders for review.

---

## How We Built It  
- **Model Training:**  
  - Used **PyTorch** and **Ultralytics** (YOLO creators) to fine-tune models.  
  - Experimented with pretrained models and custom training on the **Roboflow Construction Site Safety Dataset**.  

- **Stream Processing:**  
  - Camera input handled with **OpenCV (cv2)**.  
  - Detection pipeline built with **ultralytics** inference.  

- **Report Generation:**  
  - Implemented a **state machine** to group similar states (e.g., multiple consecutive frames missing helmets) to reduce noise.  
  - Reports are serialized and sent via HTTP requests to downstream AI agents.  

---

## Challenges We Ran Into  
- **MemryX Compiler Incompatibility:**  
  - The Neural Compiler could not handle `MatMul` operations used in YOLO11’s architecture.  
  - Tried workarounds:  
    - Replacing the operator with **onnx-graphsurgeon**.  
    - Exploring older models for compatibility.  
  - Time constraints forced us to abandon MemryX acceleration for the prototype.  

---

## Accomplishments That We’re Proud Of  
- Successfully fine-tuned **YOLO11-nano** with Roboflow’s dataset, achieving ~**70% accuracy** on static images.  
- Built a working end-to-end pipeline (camera → detection → reporting → AI agent analysis).  
- Explored **graph-level optimization** of deep learning models.  
- Pioneered the integration of **agentic AI** into real-world compliance monitoring.  

---

## What We Learned  
- Hands-on experience with **object detection models**, their architectures, and deployment limitations.  
- Gained exposure to **ONNX graphs** and low-level operator representations.  
- Understood the challenges of **edge deployment** and the complexity of hardware accelerators.  
- Learned the importance of **scoping**: our project ambition exceeded the hackathon timeframe, but the insights were invaluable.  

---

## What’s Next  
- Train or adapt a model that is **MemryX Neural Compiler compatible**.  
- Improve **accuracy and robustness** for real-time video detection.  
- Deploy on **edge devices** to allow on-site, low-latency, and resource-efficient monitoring.  
- Extend the reporting pipeline with **legal AI agents** to produce full compliance reports, not just alerts.  

---

## Built With  
- [cv2 (OpenCV)](https://opencv.org/)  
- [fetch.ai](https://fetch.ai/)  
- [Python](https://www.python.org/)  
- [PyTorch](https://pytorch.org/)  
- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)  


