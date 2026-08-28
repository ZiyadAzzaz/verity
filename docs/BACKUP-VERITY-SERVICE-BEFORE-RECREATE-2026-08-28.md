# Verity Cloud Run Service Backup Before Clean Recreation

**Captured:** 2026-08-28  
**Project:** `verity-506800`  
**Region:** `us-central1`  
**Service:** `verity`  
**Git revision at capture:** `acc16efe18f5ce5731310ff6eab6c6aa7fd98941`

This is the pre-deletion backup record required by the owner-authorized clean recreation. Secret
Manager references are recorded, but no secret value or credential is present.

## Full observed service configuration

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  annotations:
    run.googleapis.com/client-name: gcloud
    run.googleapis.com/client-version: 582.0.0
    run.googleapis.com/ingress: all
    run.googleapis.com/ingress-status: all
    run.googleapis.com/maxScale: '20'
    run.googleapis.com/operation-id: a398fa0f-c705-4adc-a6e8-b1e43e22141e
    run.googleapis.com/urls: '["https://verity-291098081728.us-central1.run.app","https://verity-7pauedpknq-uc.a.run.app"]'
    serving.knative.dev/creator: ziyadazzazdesigner@gmail.com
    serving.knative.dev/lastModifier: ziyadazzazdesigner@gmail.com
  creationTimestamp: '2026-08-27T15:39:54.095032Z'
  generation: 1
  labels:
    cloud.googleapis.com/location: us-central1
    created-by: adk
  name: verity
  namespace: '291098081728'
  resourceVersion: AAZaCSbe6Bg
  selfLink: /apis/serving.knative.dev/v1/namespaces/291098081728/services/verity
  uid: ee40dbe7-c3c6-412b-af7c-3432a97bb9c8
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: '2'
        run.googleapis.com/client-name: gcloud
        run.googleapis.com/client-version: 582.0.0
        run.googleapis.com/cpu-throttling: 'false'
        run.googleapis.com/startup-cpu-boost: 'true'
      labels:
        client.knative.dev/nonce: ibfnlfbmxw
        created-by: adk
        run.googleapis.com/startupProbeType: Default
    spec:
      containerConcurrency: 4
      containers:
      - env:
        - name: VERITY_ENV
          value: cloud
        - name: VERITY_ENVIRONMENT
          value: production
        - name: VERITY_GEMINI_MODEL
          value: gemini-3.5-flash
        - name: VERITY_REPORT_REPO
          value: ZiyadAzzaz/verity-reports
        - name: GOOGLE_CLOUD_PROJECT
          value: verity-506800
        - name: GOOGLE_CLOUD_LOCATION
          value: us-central1
        - name: GOOGLE_CLOUD_VERTEX_LOCATION
          value: global
        - name: GOOGLE_GENAI_USE_VERTEXAI
          value: 'true'
        - name: VERITY_PUBSUB_OIDC_AUDIENCE
          value: https://verity.internal/pubsub/verity-506800
        - name: VERITY_PUBSUB_SERVICE_ACCOUNT
          value: verity-pubsub@verity-506800.iam.gserviceaccount.com
        - name: AGENT_VERSION
          value: 1cc45ee04507
        - name: ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS
          value: 'false'
        - name: APP_URL
          value: https://verity-291098081728.us-central1.run.app
        - name: VERITY_API_KEY
          valueFrom:
            secretKeyRef:
              key: latest
              name: verity-api-key
        - name: VERITY_GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              key: latest
              name: verity-github-token
        image: us-central1-docker.pkg.dev/verity-506800/verity/verity-api@sha256:6a708965b91b6eab0602d17aa7b11807675c6c22f15d47bcd7a08647077f6326
        ports:
        - containerPort: 8080
          name: http1
        resources:
          limits:
            cpu: '1'
            memory: 2Gi
        startupProbe:
          failureThreshold: 1
          periodSeconds: 240
          tcpSocket:
            port: 8080
          timeoutSeconds: 240
      serviceAccountName: verity-app@verity-506800.iam.gserviceaccount.com
      timeoutSeconds: 300
  traffic:
  - latestRevision: true
    percent: 100
status:
  address:
    url: https://verity-7pauedpknq-uc.a.run.app
  conditions:
  - lastTransitionTime: '2026-08-27T15:40:13.612056Z'
    status: 'True'
    type: Ready
  - lastTransitionTime: '2026-08-27T15:40:03.119495Z'
    status: 'True'
    type: ConfigurationsReady
  - lastTransitionTime: '2026-08-27T15:40:13.544582Z'
    status: 'True'
    type: RoutesReady
  latestCreatedRevisionName: verity-00001-twb
  latestReadyRevisionName: verity-00001-twb
  observedGeneration: 1
  traffic:
  - latestRevision: true
    percent: 100
    revisionName: verity-00001-twb
  url: https://verity-7pauedpknq-uc.a.run.app
```

## Full observed service IAM policy

```yaml
etag: BwZaEhqsPow=
version: 1
```

There were no IAM bindings: no `allUsers`, push identity, operator, or other Invoker member.

## Recreation invariants

- exact pinned API digest shown above;
- application service account `verity-app@verity-506800.iam.gserviceaccount.com`;
- all 13 plain environment variables and both Secret Manager references;
- 1 vCPU, 2 GiB, concurrency 4, timeout 300 seconds;
- revision max instances 2 and min instances 0/default;
- CPU throttling disabled and startup CPU boost enabled;
- ingress `all`, default URL enabled, private IAM policy;
- port 8080 and default TCP startup probe; and
- 100% traffic to the new latest revision after it becomes Ready.

System-generated identifiers, timestamps, resource versions, operation IDs, nonces, and revision
names must change on recreation and are not invariants.
