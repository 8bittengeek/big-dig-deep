# High Level System Architecture

Diagram shows the major components and how they inter-connect.

```mermaid
flowchart LR
    subgraph Client
        QApp[Q-App Frontend]
    end

    subgraph API_Server
        API[Backend Python API]
    end

    subgraph CrawlerService
        Crawler[Snapshot + Crawler Worker]
        Packager[Archive Packager]
    end

    subgraph Qortal_Network
        QDN[Qortal Data Network QDN]
        BC[Qortal Blockchain]
    end

    QApp -->|Submit URL| API
    API -->|Queue Job| Crawler
    Crawler --> Packager
    Packager -->|Manifest + Chunks| QDN
    Packager -->|Hash| BC
    QApp -->|Fetch Archive| QDN
    QApp -->|Resolve Metadata| API
```
# Backend Subsystem Breakdown

Diagram focuses on internal components of the Python backend and how they relate.

```mermaid
flowchart TB
    subgraph Backend_API
        API_Router[API Router FastAPI]
        JobQueue[Job Queue]
        DB[Metadata DB]
    end

    subgraph Worker_Pool
        CrawlWorker[Crawl Worker]
        PackWorker[Packager Worker]
    end

    API_Router -->|enqueue| JobQueue
    JobQueue --> CrawlWorker
    CrawlWorker --> DB
    CrawlWorker --> PackWorker
    PackWorker --> DB
```

# Crawler + Archival Subsystem

Diagram detailes flow for generating snapshots

```mermaid
flowchart LR
    UserReq[URL Request]
    Headless[Headless Browser Playwright]
    StaticFetch[HTTP Fetch]
    ProcHTML[Process DOM & Resources]
    Screenshot[Screenshot]
    WARCGen[WARC Generation optional]
    AssetStore[Local Asset Store]
    ManifestGen[Manifest JSON]

    UserReq --> Headless
    Headless --> ProcHTML
    Headless --> Screenshot
    ProcHTML --> StaticFetch
    StaticFetch --> AssetStore
    Screenshot --> AssetStore
    WARCGen --> AssetStore
    AssetStore --> ManifestGen
```

# Qortal Integration Flow

Diagram shows how packaging and QDN interaction works

```mermaid
flowchart TB
    Manifest[Archive Manifest]
    Chunker[Chunk + Encrypt]
    QDN
    Blockchain[Qortal Blockchain]
    Fetcher[Q-App Fetch Module]

    Manifest --> Chunker
    Chunker --> QDN
    Chunker --> Blockchain
    QDN --> Fetcher
    Blockchain --> Fetcher
```

# Q-App Frontend Flow

Diagram outlines user interactions via the decentralized frontend

```mermaid
flowchart LR
    User[User in Browser]
    QAppUI[Q-App UI]
    QortalAPI[QDN Fetch API]
    BackendAPI

    User --> QAppUI
    QAppUI -->|Submit| BackendAPI
    QAppUI -->|Get Archive| QortalAPI
    QAppUI -->|Get Metadata| BackendAPI
```
