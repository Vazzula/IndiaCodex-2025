# Cardano-Hackathon

**Aegis: Workflow and Process Automation Engine**
Aegis is a robust workflow and process automation engine designed to optimize operations within a physical warehouse environment. The system automates and manages key logistical processes, specifically focusing on the movement and handling of vehicles during the loading and unloading phases.

Core Functionality: The Wave System
The central concept in Aegis is the wave, which represents a complete cycle of vehicle movement from the queuepad to the final loading area. The system utilizes a visual light-based feedback mechanism to guide and track vehicles, ensuring a streamlined and efficient process.

The wave's lifecycle is tracked in real-time, with status updates stored in the waveDaily table.

Initial State (Queuepad): As vehicles are prepared for their turn, the lights at the queuepad change to green in sequential order, from lane 1 to lane n.

Launchpad Arrival: Upon reaching the launchpad, the lights are red, indicating that the lane is occupied.

Loading Process: As each lane fills up, its corresponding light begins to blink yellow, signaling that the loadout process is underway.

Wave Completion: Once all vehicles have finished their loadout, the lights turn to a solid yellow, and finally, green. This transition marks the successful completion of a wave.

Getting Started
To get the project up and running locally, follow these steps

1. git clone the repo
2. Install dependencies
3. Run aegis service main