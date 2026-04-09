import type { Session } from "./types";

export const mockSessions: Session[] = [
  {
    id: "s1",
    name: "Quadcopter PID Tuning",
    date: "Apr 9",
    status: "running",
    domain: "Control",
    cards: [
      {
        id: "c1",
        type: "user",
        timestamp: "10:02 AM",
        content: {
          message:
            "Find optimal PID gains for a quadcopter hover controller. I want to minimize oscillation while maintaining fast response to step inputs. The sim should model wind disturbances.",
        },
      },
      {
        id: "c2",
        type: "research",
        timestamp: "10:03 AM",
        content: {
          summary:
            "Found 3 relevant sim frameworks. PyBullet has a quadcopter env. Prior work suggests Ziegler-Nichols as baseline, but modern approaches use Bayesian optimization over the gain space.",
          agents: [
            {
              name: "Prior Work",
              query: "PID tuning quadcopter autonomous optimization",
              findings:
                "Ziegler-Nichols method provides reasonable starting gains but tends to overshoot. Recent work (Chen 2024) uses Bayesian optimization over (Kp, Ki, Kd) space with a reward combining settling time + overshoot penalty. Found 3 papers with open-source implementations.",
              status: "done",
            },
            {
              name: "Data Sources",
              query: "Quadcopter simulation environments with wind models",
              findings:
                "PyBullet has gym-pybullet-drones (MIT license) with wind disturbance support. Gazebo is higher fidelity but heavy. AirSim is deprecated. Recommendation: PyBullet for fast iteration, validated against real flight data in 2 papers.",
              status: "done",
            },
            {
              name: "Sim Approaches",
              query: "Lightweight quadcopter dynamics simulation PID",
              findings:
                "For PID tuning specifically, a simplified 1-DOF attitude model is sufficient (reduces to spring-damper). Full 6-DOF only needed for trajectory tracking. Can run 1000 episodes in ~30 seconds on CPU.",
              status: "done",
            },
            {
              name: "Constraints",
              query: "PID gain bounds quadcopter stability",
              findings:
                "Kp: [0.1, 10.0], Ki: [0.0, 2.0], Kd: [0.01, 5.0] are safe ranges. Ki > 2.0 causes integral windup. Kd > 5.0 amplifies sensor noise. The sim should clip gains to these bounds.",
              status: "done",
            },
          ],
        },
      },
      {
        id: "c3",
        type: "engineering",
        timestamp: "10:05 AM",
        content: {
          summary:
            "Built PyBullet quadcopter sim with wind disturbance model. Baseline PID (Kp=1.0, Ki=0.1, Kd=0.5) achieves reward 312.4. Stream connected to UI.",
          status: "done",
          trace: [
            "[10:05:12] Starting environment build...",
            "[10:05:14] Installing gym-pybullet-drones via pip",
            "[10:05:31] Download complete. Setting up workspace.",
            "[10:05:33] Writing harness/run.sh -- runs episode with given gains",
            "[10:05:34] Writing harness/evaluate.sh -- extracts reward metric",
            "[10:05:35] Writing workspace/controller.py -- PID controller with configurable gains",
            "[10:05:36] Writing workspace/config.yaml -- gain values (mutable)",
            "[10:05:38] Running baseline validation...",
            "[10:05:52] Baseline complete: reward=312.4, settling_time=2.8s, overshoot=34%",
            "[10:06:01] Setting up stream relay to UI...",
            "[10:06:03] Stream connected. Handing off to scientist.",
          ],
          simSpec: {
            name: "quadcopter-pid-hover",
            metric: "reward",
            direction: "maximize",
            timeoutSeconds: 30,
          },
        },
      },
      {
        id: "c4",
        type: "simulation",
        timestamp: "10:06 AM",
        content: {
          windowCount: 1,
          maxWindows: 4,
          connected: true,
        },
      },
      {
        id: "c5",
        type: "experiment",
        timestamp: "10:06 AM",
        content: {
          experiments: [
            {
              id: 7,
              status: "running",
              description: "Kd=2.5 with derivative filter tau=0.02",
              reasoning:
                "Experiments #5 and #6 both improved by increasing Kd. But raw derivative is noisy. Adding a low-pass filter on the D term should let us push Kd higher without amplifying noise.",
              elapsed: 18,
              budget: 30,
            },
            {
              id: 6,
              status: "kept",
              metric: 891,
              prevMetric: 847,
              description: "Increased Kd from 1.0 to 2.0",
              reasoning:
                "Derivative gain has been the most impactful parameter so far. Doubling it from the baseline improved settling time significantly in #5. Let's push it further.",
              diff: "- Kd: 1.0\n+ Kd: 2.0",
            },
            {
              id: 5,
              status: "kept",
              metric: 847,
              prevMetric: 624,
              description: "Kp=3.0, Kd=1.0 with anti-windup clamp",
              reasoning:
                "Prior work suggests higher Kp with derivative damping. Adding anti-windup to prevent Ki saturation during large step changes.",
              diff: "- Kp: 1.0\n- Ki: 0.1\n- Kd: 0.5\n+ Kp: 3.0\n+ Ki: 0.1\n+ Kd: 1.0\n+ anti_windup: true",
            },
            {
              id: 4,
              status: "discarded",
              metric: 580,
              prevMetric: 624,
              description: "Ki=0.5 for steady-state error",
              reasoning:
                "The baseline has steady-state offset due to low Ki. Increasing it should reduce offset, but risk is overshoot from integral windup.",
            },
            {
              id: 3,
              status: "crash",
              description: "Kp=8.0 aggressive proportional gain",
              reasoning:
                "Testing upper bound of Kp range to see if pure proportional control can achieve fast response.",
            },
            {
              id: 2,
              status: "kept",
              metric: 624,
              prevMetric: 312,
              description: "Kp=2.0 doubled proportional gain",
              reasoning:
                "Baseline Kp=1.0 has slow response. Literature suggests quadcopter hover benefits from higher proportional gains. Starting with 2x.",
              diff: "- Kp: 1.0\n+ Kp: 2.0",
            },
            {
              id: 1,
              status: "baseline",
              metric: 312,
              description: "Baseline: Kp=1.0, Ki=0.1, Kd=0.5",
            },
          ],
        },
      },
    ],
  },
  {
    id: "s2",
    name: "LLM Pretraining",
    date: "Apr 8",
    status: "completed",
    domain: "ML",
    cards: [],
  },
  {
    id: "s3",
    name: "Portfolio Optimization",
    date: "Apr 7",
    status: "completed",
    domain: "Economics",
    cards: [],
  },
  {
    id: "s4",
    name: "Bridge Topology",
    date: "Apr 5",
    status: "failed",
    domain: "Physics",
    cards: [],
  },
];
