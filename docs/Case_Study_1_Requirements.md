

<!-- Start of picture text -->
TATA,<br>TATA ELXSI<br><!-- End of picture text -->



<!-- Start of picture text -->
 TELIPGRT<br>\ Script Your Future Season4 |<br><!-- End of picture text -->

**THINK. BUILD. CREATE. WIN** 

CASE STUDY 1 



<!-- Start of picture text -->
TELIPORT<br>Script Your Future ‘Season 4 |<br><!-- End of picture text -->

## Self-Healing Machines: Predictive Maintenance for a Connected Fleet 

### Background & Problem Statement 

A fleet of connected machines - trucks, buses, or industrial compressors - continuously streams sensor data such as vibration, temperature, motor current, pressure and RPM. Today, failures are mostly caught after a breakdown or through fixed service intervals, leading to unplanned downtime and higher maintenance cost. 

The team must build a closed-loop system that ingests this sensor data, detects early signs of degradation, predicts how much useful life a machine has left, and then automatically raises a maintenance work order - with a human stepping in only for exceptions. 

### What the Team Must Demonstrate 



<!-- Start of picture text -->
Layer<br><!-- End of picture text -->



<!-- Start of picture text -->
Data Engineering<br>Machine Learning<br>MLOps<br>Agents (non-LLM)<br><!-- End of picture text -->

### What to build 

Read the sensor data (batch or streaming), clean it - handle missing values and basic noise - and create simple rolling-window features (e.g., averages, trends) for the model. 

Detect abnormal behavior and predict the Remaining Useful Life (RUL) - how many cycles a machine has left before failure. 

Track experiments and model versions and show a simple retraining flow when new data arrives, with a basic monitoring view. 

A rule-based Triage Agent that reads the model output, decides the severity, and automatically creates a maintenance work order. No LLM required. 

### Ground Rules 

- Failures are less common than normal reading, so the model should handle mild imbalance. 

- The pipeline should run end-to-end without manual steps once data is provided. 

- Keep it lightweight - no LLM. The agent should use simple rules or thresholds. 

- Use open-source tools; document the design clearly so it can be explained in a review. 

### Dataset 

Use the NASA C-MAPSS Turbofan Engine Degradation dataset - a well-documented benchmark of medium complexity. It contains run-to-failure sensor readings from a fleet of engines (21 sensors + 3 operating settings), with true Remaining Useful Life values provided for evaluation. 

The dataset comes in four subsets (FD001–FD004) of increasing difficulty. You may choose to work with just one subset (FD001 is the simplest, and a good starting point) or take on all four for a more challenging solution. 

Official (NASA) | data.nasa.gov/dataset/cmapss-jet-engine-simulated-datadata.nasa.gov/dataset/cmapss-jet-engine-simulated-data 



<!-- Start of picture text -->
<p<br>TATA<br>TATA ELXSI<br><!-- End of picture text -->

THINK | BUILD | CREATE | WIN 



<!-- Start of picture text -->
TELIP@RTScript Your Future “Season4)<br><!-- End of picture text -->

Round-wise Deliverables 

# Round 1 (Idea Submission) – Design deck Round 2 (Detailed Submission) - Proof of Concept ~~ES~~ •  Architecture diagram: data •   Working pipeline on the chosen C-MAPSS subset(s) 

- Working pipeline on the chosen C-MAPSS subset(s) 

→ features  → model → agent → work order 

- Approach for cleaning data and building features 

   - Trained model with RUL predictions 

- Choice of anomaly-detection and RUL models, with reasoning 

   - A simple monitoring dashboard 

   - Agent auto-generating a work order + a demo retraining run 

- Logic the Triage Agent will use 

### Suggested Tools 

These are optional starting points - you are free to use alternatives. The choice of models and algorithms is left entirely to the team. 

Layer Suggested tools / libraries ~~SS~~ 

Data Engineering 



<!-- Start of picture text -->
Machine Learning<br>MLOps<br>Agent<br><!-- End of picture text -->

Python, Pandas, NumPy; optionally PySpark for larger-scale processing 

scikit-learn; optionally TensorFlow or PyTorch 

MLflow for experiment and model tracking; Streamlit or Dash for a simple dashboard 

Plain Python for rule-based logic - no LLM or agent framework required 



<!-- Start of picture text -->
TATA<br>qp<br>TATA ELXSI<br><!-- End of picture text -->

THINK | BUILD | CREATE | WIN 



<!-- Start of picture text -->
TELIPORT<br><!-- End of picture text -->

Round 1 - Evaluation of Design 

Round 1 submission are design and Architecture slides deck. The evaluation at this phase focuses on the clarity, completeness and soundness of the proposed design. 

|Criterion<br>rr|Weight<br>ee|Assessed on<br>ee|
|---|---|---|
|Problem understanding|15%|Demonstrates a clear and accurate grasp of the problem<br>and its objectives.|
|Architecture clarity|20%|Presents a coherent, well-organized design with clearly<br>defined components and how they connect.|
|Data engineering approach|15%|Proposes a sound, well-reasoned approach to preparing<br>and transforming the input data.|
|ML approach & reasoning|20%|Selects suitable methods and justifies them with clear<br>reasoning; shows awareness of practical challenges.|
|MLOps & agent logic|15%|Describes a practical operational plan and a clear, logical<br>decision flow for the agent.|
|Dataset coverage|10%|Design accounts for the varying complexity of the available<br>data and scales its approach accordingly.|
|Communication quality|5%|Well-structured, unambiguous and internally consistent.|



Round 2 - Evaluation of Proof of Concept 

Round 2 is a working build, and the review focus shifts from plan to execution. 

|Criterion<br>EE|Weight<br>ee|Assessed on|
|---|---|---|
|Working pipeline|20%|Runs end-to-end and produces results with minimal manual<br>intervention.|
|Data engineering quality|15%|Data handling is clean, robust and reproducible.|
|Model performance|15%|Produces credible results with appropriate, sensibly<br>interpreted metrics.|
|MLOps in action|10%|Operational elements are functional and demonstrable.|
|Agent behavior|10%|The agent acts correctly and reliably on the model output.|
|Dataset coverage<br>en|10%<br>ee|Depth and breadth of data tackled relative to the available<br>complexity.|
|Demo & explanation<br>|20%<br>|Team articulates its choices, trade-offs and potential<br>improvements convincingly.|





<!-- Start of picture text -->
=<br>TATA<br>TATA ELXS!<br><!-- End of picture text -->

THINK | BUILD | CREATE | WIN 

