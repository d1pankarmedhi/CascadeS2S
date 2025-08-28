# Speech2Text
An End to End Speech to Text system

# Getting started

1. Setup `minikube` in your system. 
2. Start the minikube k8 cluster and verify
   ```
   minikube start
   minikube status
   kubectl cluster-info
   ```
3. Point shell to minikube docker daemon
   ```
   eval $(minikube docker-env)
   ```
4. Build docker image
   ```
   docker build -t stt-service:v1.0.0 .
   ```

```
--- Benchmark Results for 1 worker---
Total jobs: 20
Successfully completed jobs: 18
Failed jobs: 2
Average time per job: 30.72 seconds
Maximum time per job: 59.03 seconds
Minimum time per job: 3.23 seconds
```

