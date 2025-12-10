# FORK SSO-MONITOR

This fork was modified to make SSO-Monitor work for our system.
We copied the `searxng/` folder and checked out commit 8a4104b99 using `git checkout 8a4104b99`.
We modified the docker compose `docker-compose.yml` so that the `searxng` service uses the version we copied.

## EXTERNAL IP

To set an external IP (in our case connected to Tailscale), you need to create a `.env` file inside `SSO-MONITOR/` with the content `TAILSCALE_IP=NN.NN.NN.NN` (substitute the IP if it's different). If TAILSCALE_IP is empty, SSO-MONITOR will run only on localhost; otherwise, it will run only on the defined IP.

The modifications below are not needed; we left them there just to remember the operations that we performed.

## Make it work

### 1. Create a local container for searxng

Since version 2023.12.11-8a4104b99 (used in the tool) is not available on Docker Hub, we have to create our own:

1. Clone the searxng repository at https://github.com/searxng/searxng.git
2. Check out commit 8a4104b99 using `git checkout 8a4104b99`
3. Build the Docker image using `docker build -t searxng/searxng:2023.12.11-8a4104b99 .` inside the searxng directory

### 2. Update Pipfile versions

There are many conflicts regarding Python libraries; use the Pipfile.lock to check the correct versions for

- brain
- cookie-store
- worker

### 3. Update IP addresses

If you want to access the tool from a different host, update docker-compose.yml by changing every **127.0.0.1:port** to **0.0.0.0:port**

To make things easier, change the href links of the buttons inside the _brain/template/views/admin.html_ file to **server_ip:server_port** so you don't have to manually change the port in the URL each time.

### 4. Select the correct queue

To assign the workers to a different queue, change the line `RABBITMQ_QUEUE=${RABBITMQ_QUEUE:-<name_of_the_queue>}` inside _docker-compose.yml_ in the **worker** service to the one you're interested in:

- `RABBITMQ_QUEUE=${RABBITMQ_QUEUE:-landscape_analysis_treq}`
- `RABBITMQ_QUEUE=${RABBITMQ_QUEUE:-login_trace_analysis_treq}`
- `RABBITMQ_QUEUE=${RABBITMQ_QUEUE:-wildcard_receiver_analysis_treq}`

### 5. Make a Login Trace Analysis

The default username and password is `admin:changeme`.

To make a Login Trace Analysis you must first:

- Perform a landscape analysis of the target website
- Then change the RABBITMQ_QUEUE to login_trace_analysis_treq

After that, fill in the fields using the _task_id_ field from the previous Landscape Analysis, and provide the correct parameters for the Google SSO.
After a while, the results will be stored in the MinIO database and in MongoDB.
