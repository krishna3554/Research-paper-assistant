export const collections = [
  { id: "nlp-survey", name: "NLP Survey", count: 12 },
  { id: "cv-transformers", name: "CV Transformers", count: 19 },
  { id: "rag-methods", name: "RAG Methods", count: 8 },
  { id: "clinical-nli", name: "Clinical NLI", count: 6 }
];

export const papers = [
  {
    id: "vaswani-2017",
    title: "Attention Is All You Need",
    authors: "Vaswani et al.",
    year: 2017,
    collection: "nlp-survey",
    type: "Transformer",
    status: "indexed",
    citations: 124,
    confidence: 0.94,
    abstract:
      "Introduces the Transformer architecture and replaces recurrence with scaled dot-product attention.",
    methodology:
      "Encoder-decoder network, 8 attention heads, residual connections, Adam optimizer, WMT translation benchmarks.",
    tags: ["attention", "architecture", "translation"],
    color: "mint"
  },
  {
    id: "devlin-2018",
    title: "BERT: Pre-training of Deep Bidirectional Transformers",
    authors: "Devlin et al.",
    year: 2018,
    collection: "nlp-survey",
    type: "BERT",
    status: "indexed",
    citations: 96,
    confidence: 0.91,
    abstract:
      "Uses masked language modeling and next sentence prediction for bidirectional pre-training.",
    methodology:
      "Transformer encoder, 12 layers for base, BooksCorpus plus Wikipedia, masked token prediction.",
    tags: ["pretraining", "encoder", "language model"],
    color: "cream"
  },
  {
    id: "brown-2020",
    title: "Language Models are Few-Shot Learners",
    authors: "Brown et al.",
    year: 2020,
    collection: "nlp-survey",
    type: "Scaling",
    status: "conflict",
    citations: 88,
    confidence: 0.89,
    abstract:
      "Shows that larger autoregressive language models can perform many tasks from prompts alone.",
    methodology:
      "Autoregressive decoder, 96 attention heads at largest scale, web-scale corpus, few-shot evaluation.",
    tags: ["scaling", "few-shot", "decoder"],
    color: "rose"
  },
  {
    id: "lewis-2020",
    title: "Retrieval-Augmented Generation for Knowledge-Intensive NLP",
    authors: "Lewis et al.",
    year: 2020,
    collection: "rag-methods",
    type: "RAG",
    status: "indexed",
    citations: 57,
    confidence: 0.87,
    abstract:
      "Combines parametric generation with non-parametric retrieval over dense document indexes.",
    methodology:
      "Dense passage retriever, BART generator, marginalization over retrieved documents, open-domain QA.",
    tags: ["retrieval", "generation", "qa"],
    color: "blue"
  },
  {
    id: "dosovitskiy-2020",
    title: "An Image is Worth 16x16 Words",
    authors: "Dosovitskiy et al.",
    year: 2020,
    collection: "cv-transformers",
    type: "Vision",
    status: "indexed",
    citations: 72,
    confidence: 0.86,
    abstract:
      "Applies a pure Transformer architecture to image patches for large-scale image recognition.",
    methodology:
      "Patch embeddings, Transformer encoder, supervised pre-training on large image datasets.",
    tags: ["vision", "patches", "classification"],
    color: "amber"
  }
];

export const answers = [
  {
    id: "a1",
    role: "assistant",
    body:
      "I've indexed 12 papers in your NLP Survey collection. I found 3 conflicts around model scaling efficiency, 4 methodology clusters, and 2 under-cited benchmark assumptions.",
    sources: []
  },
  {
    id: "q1",
    role: "user",
    body: "What does Vaswani et al. say about attention head count?",
    sources: []
  },
  {
    id: "a2",
    role: "assistant",
    body:
      "The original Transformer uses 8 parallel attention heads. Each head operates on a 64-dimensional subspace when d_model is 512, allowing the model to attend to different representation subspaces at different positions.",
    sources: [
      { paperId: "vaswani-2017", label: "Vaswani et al., 2017", section: "Section 3.2", page: "p. 5" }
    ]
  }
];

export const claims = [
  {
    id: "c1",
    paperId: "brown-2020",
    tone: "violet",
    text: "Uses 96 attention heads at the largest GPT-3 scale."
  },
  {
    id: "c2",
    paperId: "devlin-2018",
    tone: "green",
    text: "BERT-base uses 12 attention heads with bidirectional encoder layers."
  },
  {
    id: "c3",
    paperId: "lewis-2020",
    tone: "blue",
    text: "Retrieval improves factual specificity for knowledge-intensive tasks."
  }
];

export const conflicts = [
  {
    id: "conflict-1",
    severity: "high",
    title: "Scaling efficiency",
    papers: ["vaswani-2017", "brown-2020"],
    detail:
      "Claims disagree on whether adding heads or increasing representation width drives most of the observed quality gains."
  },
  {
    id: "conflict-2",
    severity: "medium",
    title: "Retrieval vs parametric memory",
    papers: ["brown-2020", "lewis-2020"],
    detail:
      "Few-shot prompting reduces supervision, while retrieval-augmented generation argues external memory improves factuality."
  },
  {
    id: "conflict-3",
    severity: "medium",
    title: "Benchmark comparability",
    papers: ["devlin-2018", "brown-2020"],
    detail:
      "Evaluation setups mix fine-tuned and prompted regimes, which can make direct score comparison misleading."
  }
];

export const reviewSections = [
  {
    id: "chronology",
    title: "Chronological synthesis",
    text:
      "Transformer research moves from architecture simplification in 2017, to bidirectional pre-training in 2018, to scale-driven few-shot behavior and retrieval grounding in 2020."
  },
  {
    id: "methodology",
    title: "Methodology clusters",
    text:
      "The corpus clusters into encoder-only pre-training, decoder-only scaling, retrieval-augmented generation, and cross-modal patch-based Transformer adaptation."
  },
  {
    id: "gap",
    title: "Open gap",
    text:
      "Only two papers report comparable ablations for attention head count under fixed compute, making head-count efficiency an under-supported claim."
  }
];
