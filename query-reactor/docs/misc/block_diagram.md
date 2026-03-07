graph TD
    A[User with History] --> B(QA with Human)
    B --> C{Query Pre-process}
    C --> D{Query Router}

    D --> E[Simple Retrieval]
    D --> F[Internet Retrieval]
    D --> G[Multi-Retrieval with multi-steps]

    subgraph Retrieval Process
        E --> H(Retrieval quality check)
        F --> I(Retrieval quality check)
        G --> J(Retrieval quality check)
    end
    
    H --> K[Documents]
    I --> K
    J --> K

    K --> L[re-ranking]
    L --> M(Smart Retrieval)
    M --> N(Answer create)
    N --> O(Answer Check)
    O --> P[Answer]

    subgraph RAG Databases
        Q[Vector DB]
        R[Text DB]
        S[Graph DB]
        T[XYZ DB]
    end

    %% Feedback Loops
    M -- Feedback --> C
    N -- Feedback --> C
    O -- Feedback --> M