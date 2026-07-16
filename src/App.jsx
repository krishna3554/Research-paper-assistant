import { useEffect, useMemo, useState } from "react";
import {
  ArrowUpRight,
  BookOpen,
  Boxes,
  BrainCircuit,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  FilePlus2,
  GitCompareArrows,
  Library,
  MessageSquareText,
  Network,
  PanelLeft,
  Search,
  Send,
  Sparkles,
  Upload,
  X
} from "lucide-react";
import { answers, claims, collections as seedCollections, conflicts, papers, reviewSections } from "./data/researchData";
import {
  askQuestion,
  getComparison,
  getConflicts,
  getGraph,
  getPaperStatus,
  getPapers,
  getReview,
  ingestSourceUrl,
  uploadPaper
} from "./lib/api";

const tabs = [
  { id: "qa", label: "Q&A", icon: MessageSquareText },
  { id: "review", label: "Review", icon: BookOpen },
  { id: "compare", label: "Compare", icon: GitCompareArrows },
  { id: "graph", label: "Graph", icon: Network }
];

const filters = ["All", "Methodology", "Scaling", "Retrieval", "Conflicts"];
const COLLECTIONS_STORAGE_KEY = "papermind.collections";
const PAPER_COLLECTIONS_STORAGE_KEY = "papermind.paperCollections";

function classNames(...values) {
  return values.filter(Boolean).join(" ");
}

function slugify(value) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function readJsonStorage(key, fallback) {
  try {
    return JSON.parse(window.localStorage.getItem(key)) ?? fallback;
  } catch {
    return fallback;
  }
}

function App() {
  const [view, setView] = useState(() => (window.location.hash === "#/workspace" ? "workspace" : "landing"));
  const [query, setQuery] = useState("");
  const [activeCollection, setActiveCollection] = useState("all");
  const [activePaperId, setActivePaperId] = useState("vaswani-2017");
  const [activeTab, setActiveTab] = useState("qa");
  const [activeFilter, setActiveFilter] = useState("All");
  const [isUploadOpen, setUploadOpen] = useState(false);
  const [isSidebarOpen, setSidebarOpen] = useState(true);
  const [userCollections, setUserCollections] = useState(() => readJsonStorage(COLLECTIONS_STORAGE_KEY, []));
  const [paperCollectionOverrides, setPaperCollectionOverrides] = useState(() => readJsonStorage(PAPER_COLLECTIONS_STORAGE_KEY, {}));
  const [uploadMode, setUploadMode] = useState("pdf");
  const [uploadStatus, setUploadStatus] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [sourceUrl, setSourceUrl] = useState("");
  const [apiPapers, setApiPapers] = useState([]);
  const [apiError, setApiError] = useState("");
  const [isLoadingPapers, setIsLoadingPapers] = useState(false);
  const [messages, setMessages] = useState(answers);
  const [isAsking, setIsAsking] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [insight, setInsight] = useState("Corpus ready: 12 indexed papers, 3 conflicts, 4 methodology clusters.");
  const [panelData, setPanelData] = useState({
    review: null,
    compare: null,
    conflicts: null,
    graph: null
  });
  const [panelStatus, setPanelStatus] = useState({
    review: "",
    compare: "",
    conflicts: "",
    graph: ""
  });

  async function refreshPapers() {
    setIsLoadingPapers(true);
    setApiError("");

    try {
      const data = await getPapers();
      setApiPapers(data);
    } catch (error) {
      setApiError(error.message);
    } finally {
      setIsLoadingPapers(false);
    }
  }

  async function handleUploadFile(event) {
    const file = event.target.files?.[0];

    if (!file) return;

    if (file.type !== "application/pdf") {
      setUploadStatus("Only PDF files are supported.");
      return;
    }

    setIsUploading(true);
    setUploadStatus("Uploading paper...");

    try {
      const result = await uploadPaper(file);
      setUploadStatus(`Uploaded ${result.filename}. Indexing started.`);
      await refreshPapers();
    } catch (error) {
      setUploadStatus(error.message);
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  }

  async function handleSourceUrlSubmit(event) {
    event.preventDefault();
    const cleanUrl = sourceUrl.trim();

    if (!cleanUrl) {
      setUploadStatus("Enter a direct PDF URL or arXiv URL.");
      return;
    }

    setIsUploading(true);
    setUploadStatus("Resolving source URL...");

    try {
      const result = await ingestSourceUrl(cleanUrl);
      setUploadStatus(`Added ${result.filename}. Indexing started.`);
      setSourceUrl("");
      await refreshPapers();
    } catch (error) {
      setUploadStatus(error.message);
    } finally {
      setIsUploading(false);
    }
  }

  async function loadPanel(kind, paperId = activePaper?.id) {
    const backendPaperId = paperId?.startsWith("paper_") ? paperId : null;

    setPanelStatus((current) => ({
      ...current,
      [kind]: "loading"
    }));

    try {
      const loaders = {
        review: () => getReview({ paperId: backendPaperId }),
        compare: () => getComparison({ paperId: backendPaperId }),
        conflicts: () => getConflicts({ paperId: backendPaperId }),
        graph: () => getGraph(backendPaperId)
      };
      const data = await loaders[kind]();

      setPanelData((current) => ({
        ...current,
        [kind]: data
      }));
      setPanelStatus((current) => ({
        ...current,
        [kind]: ""
      }));
    } catch (error) {
      setPanelStatus((current) => ({
        ...current,
        [kind]: error.message
      }));
    }
  }

  const backendPapers = apiPapers.map((paper) => ({
    id: paper.id,
    title: paper.filename.replace(/\.pdf$/i, ""),
    authors: "Uploaded paper",
    year: new Date(paper.uploaded_at).getFullYear(),
    collection: paperCollectionOverrides[paper.id] || "uploaded",
    type: paper.status,
    status: paper.status === "indexed" ? "indexed" : "processing",
    citations: 0,
    confidence: paper.status === "indexed" ? 0.82 : 0.32,
    abstract: `${paper.filename} is stored in ${paper.storage_provider} and currently marked ${paper.status}.`,
    methodology: "Uploaded through the PaperMind ingestion pipeline.",
    tags: [paper.status, paper.storage_provider],
    color: paper.status === "indexed" ? "mint" : "blue"
  }));
  const localPapers = papers.map((paper) => ({
    ...paper,
    collection: paperCollectionOverrides[paper.id] || paper.collection
  }));
  const visiblePapers = backendPapers.length > 0 ? backendPapers : localPapers;
  const collectionOptions = useMemo(() => {
    const baseOptions = [
      { id: "all", name: "Library" },
      ...seedCollections,
      { id: "uploaded", name: "Uploaded" }
    ];
    const merged = [...baseOptions, ...userCollections];
    const unique = merged.filter(
      (collection, index, list) => list.findIndex((item) => item.id === collection.id) === index
    );

    return unique.map((collection) => ({
      ...collection,
      count:
        collection.id === "all"
          ? visiblePapers.length
          : visiblePapers.filter((paper) => paper.collection === collection.id).length
    }));
  }, [userCollections, visiblePapers]);

  const filteredPapers = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return visiblePapers.filter((paper) => {
      const collectionMatch = activeCollection === "all" || paper.collection === activeCollection;
      const filterMatch =
        activeFilter === "All" ||
        paper.type.toLowerCase().includes(activeFilter.toLowerCase()) ||
        paper.tags.some((tag) => tag.toLowerCase().includes(activeFilter.toLowerCase())) ||
        (activeFilter === "Conflicts" && paper.status === "conflict");
      const queryMatch =
        !normalized ||
        [paper.title, paper.authors, paper.type, paper.abstract, paper.methodology, paper.year]
          .join(" ")
          .toLowerCase()
          .includes(normalized);
      return collectionMatch && filterMatch && queryMatch;
    });
  }, [activeCollection, activeFilter, query, visiblePapers]);

  const activePaper = visiblePapers.find((paper) => paper.id === activePaperId) ?? visiblePapers[0];
  const activeCollectionLabel =
    collectionOptions.find((collection) => collection.id === activeCollection)?.name ?? "Research Workspace";

  async function handleSubmit(event) {
    event.preventDefault();
    const cleanPrompt = prompt.trim();
    if (!cleanPrompt) return;

    const selected = activePaper;
    const questionId = `q-${Date.now()}`;
    const answerId = `a-${Date.now()}`;

    setMessages((current) => [
      ...current,
      { id: questionId, role: "user", body: cleanPrompt, sources: [] }
    ]);
    setPrompt("");
    setIsAsking(true);

    try {
      const response = await askQuestion({
        question: cleanPrompt,
        paperId: selected?.id?.startsWith("paper_") ? selected.id : null
      });

      setMessages((current) => [
        ...current,
        {
          id: answerId,
          role: "assistant",
          body: response.answer,
          sources: response.sources.map((source, index) => ({
            paperId: selected?.id ?? `source-${index}`,
            label: source.source,
            section: `Source ${index + 1}`,
            page: source.page ? `p. ${source.page}` : "indexed chunk",
            content: response.retrieved_chunks[index]?.content
          }))
        }
      ]);
      setInsight(`Generated a cited answer from ${response.sources.length} retrieved source chunk(s).`);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: answerId,
          role: "assistant",
          body: error.message,
          sources: []
        }
      ]);
      setInsight("The RAG answer failed. Check that the selected paper is indexed and LM Studio is running.");
    } finally {
      setIsAsking(false);
    }
  }

  function runAction(kind) {
    if (kind === "compare") {
      setActiveTab("compare");
      setInsight("Comparison matrix loaded: architecture, objective, data, evaluation, and limitations.");
      loadPanel("compare");
    }
    if (kind === "conflicts") {
      setActiveTab("compare");
      setActiveFilter("Conflicts");
      setInsight("Conflict detector surfaced 3 claim pairs with source-level evidence.");
      loadPanel("conflicts");
    }
    if (kind === "review") {
      setActiveTab("review");
      setInsight("Draft review refreshed with chronological and thematic synthesis sections.");
      loadPanel("review");
    }
    if (kind === "graph") {
      setActiveTab("graph");
      setInsight("Graph view focused on citation, method, and conflict links for the active source.");
      loadPanel("graph");
    }
    if (kind === "collection") {
      const name = window.prompt("Collection name");
      const cleanName = name?.trim();

      if (!cleanName) return;

      const id = slugify(cleanName) || `collection-${Date.now()}`;
      const finalId = collectionOptions.some((collection) => collection.id === id)
        ? `${id}-${Date.now()}`
        : id;

      setUserCollections((current) => [
        ...current,
        { id: finalId, name: cleanName }
      ]);

      if (activePaper?.id) {
        setPaperCollectionOverrides((current) => ({
          ...current,
          [activePaper.id]: finalId
        }));
      }

      setActiveCollection(finalId);
      setInsight(`Created ${cleanName} and added ${activePaper?.title ?? "the active paper"}.`);
    }
  }

  useEffect(() => {
    function syncRoute() {
      setView(window.location.hash === "#/workspace" ? "workspace" : "landing");
    }

    window.addEventListener("hashchange", syncRoute);
    return () => window.removeEventListener("hashchange", syncRoute);
  }, []);

  useEffect(() => {
    refreshPapers();
  }, []);

  useEffect(() => {
    window.localStorage.setItem(COLLECTIONS_STORAGE_KEY, JSON.stringify(userCollections));
  }, [userCollections]);

  useEffect(() => {
    window.localStorage.setItem(PAPER_COLLECTIONS_STORAGE_KEY, JSON.stringify(paperCollectionOverrides));
  }, [paperCollectionOverrides]);

  useEffect(() => {
    if (!visiblePapers.some((paper) => paper.id === activePaperId)) {
      setActivePaperId(visiblePapers[0]?.id ?? "");
    }
  }, [activePaperId, visiblePapers]);

  useEffect(() => {
    const selectedCollection = collectionOptions.find((collection) => collection.id === activeCollection);

    if (!selectedCollection) {
      setActiveCollection("all");
    }
  }, [activeCollection, collectionOptions]);

  useEffect(() => {
    const pending = apiPapers.filter((paper) => ["uploaded", "processing"].includes(paper.status));

    if (pending.length === 0) return undefined;

    const timer = window.setInterval(async () => {
      try {
        const statuses = await Promise.all(
          pending.map((paper) => getPaperStatus(paper.id))
        );
        const changed = statuses.some((status) => {
          const existing = apiPapers.find((paper) => paper.id === status.paper_id);
          return existing && existing.status !== status.status;
        });

        if (changed) {
          await refreshPapers();
        }
      } catch (error) {
        setApiError(error.message);
      }
    }, 3500);

    return () => window.clearInterval(timer);
  }, [apiPapers]);

  useEffect(() => {
    if (!activePaper?.id?.startsWith("paper_")) return;

    if (activeTab === "review") loadPanel("review", activePaper.id);
    if (activeTab === "compare") loadPanel("compare", activePaper.id);
    if (activeTab === "graph") loadPanel("graph", activePaper.id);
  }, [activePaperId, activeTab]);

  function navigate(nextView) {
    const nextHash = nextView === "workspace" ? "#/workspace" : "#/";
    if (window.location.hash === nextHash) {
      setView(nextView);
      return;
    }
    window.location.hash = nextHash;
  }

  if (view === "landing") {
    return <LandingPage onEnterApp={() => navigate("workspace")} />;
  }

  return (
    <WorkspacePage
      activeCollection={activeCollection}
      activeCollectionLabel={activeCollectionLabel}
      activeFilter={activeFilter}
      activePaper={activePaper}
      activePaperId={activePaperId}
      activeTab={activeTab}
      apiError={apiError}
      collectionOptions={collectionOptions}
      filteredPapers={filteredPapers}
      insight={insight}
      isLoadingPapers={isLoadingPapers}
      isSidebarOpen={isSidebarOpen}
      isUploadOpen={isUploadOpen}
      isUploading={isUploading}
      messages={messages}
      panelData={panelData}
      panelStatus={panelStatus}
      prompt={prompt}
      query={query}
      setActiveCollection={setActiveCollection}
      setActiveFilter={setActiveFilter}
      setActivePaperId={setActivePaperId}
      setActiveTab={setActiveTab}
      setPrompt={setPrompt}
      setQuery={setQuery}
      setSidebarOpen={setSidebarOpen}
      setSourceUrl={setSourceUrl}
      setUploadOpen={setUploadOpen}
      setUploadMode={setUploadMode}
      sourceUrl={sourceUrl}
      uploadMode={uploadMode}
      uploadStatus={uploadStatus}
      onAction={runAction}
      onHome={() => navigate("landing")}
      onSourceUrlSubmit={handleSourceUrlSubmit}
      onUploadFile={handleUploadFile}
      onSubmit={handleSubmit}
      isAsking={isAsking}
    />
  );
}

function LandingPage({ onEnterApp }) {
  return (
    <main className="landing-page min-h-screen bg-[#ebe8dd] text-[#1e1e19]">
      <header className="landing-nav">
        <button className="landing-brand" type="button" aria-label="PaperMind home">
          <span>
            <BrainCircuit size={22} strokeWidth={2.4} />
          </span>
          PaperMind
        </button>
        <nav aria-label="Product sections">
          <a href="#workflow">Workflow</a>
          <a href="#evidence">Evidence</a>
          <a href="#outcomes">Outcomes</a>
        </nav>
        <button className="landing-secondary" onClick={onEnterApp} type="button">
          Open app
        </button>
      </header>

      <section className="landing-hero">
        <div className="landing-copy">
          <p className="landing-kicker">AI literature intelligence for real research work</p>
          <h1>Research decisions, source-backed.</h1>
          <p>
            PaperMind reads a corpus, extracts methodology, compares claims, detects contradictions, and drafts reviews with citations kept close to every answer.
          </p>
          <div className="landing-actions">
            <button className="landing-primary" onClick={onEnterApp} type="button">
              Start in workspace
              <ArrowUpRight size={18} />
            </button>
            <a className="landing-link" href="#workflow">
              See workflow
            </a>
          </div>
        </div>

        <ProductPreview />
      </section>

      <section className="landing-band" id="workflow">
        <div>
          <p className="landing-kicker">Research workflow</p>
          <h2>Built around the jobs researchers repeat every week.</h2>
        </div>
        <div className="landing-feature-grid">
          <Feature title="Ingest" text="PDF, DOI, and arXiv inputs become structured paper records with metadata and citation maps." />
          <Feature title="Compare" text="Methodology, data, models, limitations, and evaluation choices line up across papers." />
          <Feature title="Ground" text="Answers, review paragraphs, and conflict flags stay attached to source passages." />
        </div>
      </section>

      <section className="landing-evidence" id="evidence">
        <div className="evidence-copy">
          <p className="landing-kicker">Citation-aware by design</p>
          <h2>No orphaned claims.</h2>
          <p>
            The interface is organized around corpus state, source confidence, related claims, and exportable review material instead of loose chat output.
          </p>
        </div>
        <div className="evidence-steps" aria-label="Evidence workflow">
          <span>Source chunk</span>
          <ChevronRight size={18} />
          <span>Claim alignment</span>
          <ChevronRight size={18} />
          <span>Cited answer</span>
        </div>
      </section>

      <section className="landing-outcomes" id="outcomes">
        <Metric label="Corpus scale" value="500" suffix="papers" />
        <Metric label="Citation target" value="85" suffix="%" />
        <Metric label="Review draft" value="10" suffix="min" />
        <Metric label="Conflict precision" value="75" suffix="%" />
      </section>
    </main>
  );
}

function ProductPreview() {
  return (
    <aside className="product-preview" aria-label="PaperMind product preview">
      <div className="preview-top">
        <span>NLP Survey</span>
        <strong>12 papers indexed</strong>
      </div>
      <div className="preview-question">What changed between Transformer attention and BERT pre-training?</div>
      <div className="preview-answer">
        <p>
          Transformer removes recurrence with multi-head attention; BERT keeps the encoder stack and adds masked bidirectional pre-training.
        </p>
        <span>Vaswani et al., 2017 . Devlin et al., 2018</span>
      </div>
      <div className="preview-claims">
        <span>3 conflicts</span>
        <span>4 method clusters</span>
        <span>APA export ready</span>
      </div>
    </aside>
  );
}

function Feature({ title, text }) {
  return (
    <article className="landing-feature">
      <h3>{title}</h3>
      <p>{text}</p>
    </article>
  );
}

function WorkspacePage({
  activeCollection,
  activeCollectionLabel,
  activeFilter,
  activePaper,
  activePaperId,
  activeTab,
  apiError,
  collectionOptions,
  filteredPapers,
  insight,
  isLoadingPapers,
  isSidebarOpen,
  isUploadOpen,
  isUploading,
  isAsking,
  messages,
  panelData,
  panelStatus,
  prompt,
  query,
  setActiveCollection,
  setActiveFilter,
  setActivePaperId,
  setActiveTab,
  setPrompt,
  setQuery,
  setSidebarOpen,
  setSourceUrl,
  setUploadOpen,
  setUploadMode,
  sourceUrl,
  uploadMode,
  uploadStatus,
  onAction,
  onHome,
  onSourceUrlSubmit,
  onUploadFile,
  onSubmit
}) {
  return (
    <main className="workspace-page min-h-screen bg-[#151512] text-stone-100">
      <div className="grain-overlay" />
      <TopBar
        isSidebarOpen={isSidebarOpen}
        query={query}
        setQuery={setQuery}
        onToggleSidebar={() => setSidebarOpen((current) => !current)}
        onUpload={() => setUploadOpen(true)}
        onHome={onHome}
      />

      <section className="relative mx-auto flex w-full max-w-[1540px] flex-col gap-5 px-4 pb-4 pt-4 sm:px-5 lg:px-7">
        <div className={classNames("workspace-grid min-h-[calc(100vh-104px)] overflow-hidden border border-stone-700/80 bg-[#20201c] shadow-panel", !isSidebarOpen && "sidebar-collapsed")}>
          <Sidebar
            activeCollection={activeCollection}
            collections={collectionOptions}
            setActiveCollection={setActiveCollection}
            onAction={onAction}
          />

          <PaperRail
            activeCollectionLabel={activeCollectionLabel}
            activePaperId={activePaperId}
            activeFilter={activeFilter}
            apiError={apiError}
            filteredPapers={filteredPapers}
            isLoadingPapers={isLoadingPapers}
            paperCount={filteredPapers.length}
            setActiveFilter={setActiveFilter}
            setActivePaperId={setActivePaperId}
            setUploadMode={setUploadMode}
            onUpload={() => setUploadOpen(true)}
          />

          <IntelligencePanel
            activePaper={activePaper}
            activeTab={activeTab}
            isAsking={isAsking}
            setActiveTab={setActiveTab}
            messages={messages}
            panelData={panelData}
            panelStatus={panelStatus}
            prompt={prompt}
            setPrompt={setPrompt}
            onSubmit={onSubmit}
            onAction={onAction}
            insight={insight}
          />
        </div>
      </section>

      {isUploadOpen && (
        <UploadModal
          isUploading={isUploading}
          uploadMode={uploadMode}
          uploadStatus={uploadStatus}
          sourceUrl={sourceUrl}
          setSourceUrl={setSourceUrl}
          setUploadMode={setUploadMode}
          onClose={() => setUploadOpen(false)}
          onSourceUrlSubmit={onSourceUrlSubmit}
          onUploadFile={onUploadFile}
        />
      )}
    </main>
  );
}

function TopBar({ isSidebarOpen, query, setQuery, onToggleSidebar, onUpload, onHome }) {
  return (
    <header className="workspace-topbar sticky top-0 z-30 border-b border-stone-700/80 bg-[#272722]/95 backdrop-blur">
      <div className="mx-auto grid max-w-[1540px] grid-cols-[auto_1fr_auto] items-center gap-3 px-4 py-3 sm:px-5 lg:px-7">
        <button className="flex items-center gap-3" onClick={onHome} type="button" aria-label="PaperMind home">
          <span className="grid h-11 w-11 place-items-center rounded-[8px] bg-violet-500 text-[#171713]">
            <BrainCircuit size={23} strokeWidth={2.4} />
          </span>
          <span className="hidden text-2xl font-medium tracking-normal text-stone-50 sm:block">PaperMind</span>
        </button>

        <label className="mx-auto flex h-12 w-full max-w-3xl items-center gap-3 border border-stone-600 bg-[#2c2c27] px-4 text-stone-300 focus-within:border-violet-400">
          <Search size={21} aria-hidden="true" />
          <span className="sr-only">Search papers, authors, concepts</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="w-full bg-transparent text-lg text-stone-100 outline-none placeholder:text-stone-400 sm:text-2xl"
            placeholder="Search corpus..."
          />
        </label>

        <div className="flex items-center gap-2">
          <button className="btn-outline hidden sm:inline-flex" onClick={onUpload} type="button">
            <Upload size={18} />
            Upload
          </button>
          <button className="icon-button topbar-upload-icon" onClick={onUpload} type="button" aria-label="Upload paper">
            <Upload size={19} />
          </button>
          <button
            className={classNames("icon-button topbar-panel-toggle", isSidebarOpen && "active")}
            onClick={onToggleSidebar}
            type="button"
            aria-label="Toggle library panel"
          >
            <PanelLeft size={19} />
          </button>
          <button className="grid h-11 w-11 place-items-center rounded-full bg-[#cac4ff] text-lg font-medium text-[#262149]">
            KR
          </button>
        </div>
      </div>
    </header>
  );
}

function Metric({ label, value, suffix }) {
  return (
    <div className="metric-cell">
      <span className="block text-2xl font-semibold text-stone-50">{value}</span>
      <span className="text-xs uppercase tracking-[0.18em] text-stone-500">{suffix}</span>
      <span className="mt-1 block text-sm text-stone-300">{label}</span>
    </div>
  );
}

function Sidebar({ activeCollection, collections, setActiveCollection, onAction }) {
  const libraryCount = collections.find((collection) => collection.id === "all")?.count ?? 0;
  const visibleCollections = collections.filter((collection) => collection.id !== "all");

  return (
    <aside className="workspace-sidebar hidden border-r border-stone-700/80 bg-[#282823] p-4 lg:block">
      <p className="eyebrow mb-3">Workspace</p>
      <button
        className={classNames("nav-row", activeCollection === "all" && "selected")}
        onClick={() => setActiveCollection("all")}
        type="button"
      >
        <Library size={19} />
        Library
        <span>{libraryCount}</span>
      </button>
      <button className="nav-row" onClick={() => onAction("compare")} type="button">
        <GitCompareArrows size={18} />
        Compare
      </button>
      <button className="nav-row" onClick={() => onAction("conflicts")} type="button">
        <CircleAlert size={18} />
        Conflicts
        <span>3</span>
      </button>

      <p className="eyebrow mb-3 mt-8">Collections</p>
      <div className="space-y-1">
        {visibleCollections.map((collection) => (
          <button
            className={classNames("nav-row", activeCollection === collection.id && "active")}
            key={collection.id}
            onClick={() => setActiveCollection(collection.id)}
            type="button"
          >
            <Boxes size={17} />
            {collection.name}
            <span>{collection.count}</span>
          </button>
        ))}
      </div>

      <button className="nav-row mt-8" onClick={() => onAction("collection")} type="button">
        <FilePlus2 size={18} />
        New collection
      </button>
    </aside>
  );
}

function PaperRail({
  activeCollectionLabel,
  activePaperId,
  activeFilter,
  apiError,
  filteredPapers,
  isLoadingPapers,
  paperCount,
  setActiveFilter,
  setActivePaperId,
  setUploadMode,
  onUpload
}) {
  function openUpload(mode) {
    setUploadMode(mode);
    onUpload();
  }

  return (
    <section className="paper-rail border-r border-stone-700/80 bg-[#11110f]">
      <div className="border-b border-stone-700/80 p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="eyebrow">Active corpus</p>
            <h2 className="mt-1 text-2xl font-medium leading-tight">{activeCollectionLabel}</h2>
          </div>
          <div className="flex gap-2">
            <button className="mini-toggle" onClick={() => openUpload("pdf")} type="button" aria-label="Upload PDF">
              <Upload size={15} />
            </button>
            <button className="mini-toggle" onClick={() => openUpload("doi")} type="button" aria-label="Add DOI">
              DOI
            </button>
            <button className="mini-toggle" onClick={() => openUpload("url")} type="button" aria-label="Add URL">
              URL
            </button>
          </div>
        </div>

        <button className="dropzone mt-5" onClick={() => openUpload("pdf")} type="button">
          <Upload size={23} />
          <span>Upload PDFs or add by DOI</span>
          <small>PDF upload, direct PDF URL, and arXiv URL supported</small>
        </button>

        <div className="mt-4 grid grid-cols-3 gap-2">
          <Stat value={paperCount} label="Papers" />
          <Stat value="3" label="Conflicts" />
          <Stat value="4" label="Clusters" />
        </div>
      </div>

      <div className="filters no-scrollbar border-b border-stone-700/80 px-3 py-3">
        {filters.map((filter) => (
          <button
            className={classNames("filter-pill", activeFilter === filter && "active")}
            key={filter}
            onClick={() => setActiveFilter(filter)}
            type="button"
          >
            {filter}
          </button>
        ))}
      </div>

      <div className="paper-list no-scrollbar">
        {isLoadingPapers ? (
          <div className="m-4 border border-stone-700 bg-[#20201c] p-5 text-stone-300">
            Loading papers...
          </div>
        ) : apiError ? (
          <div className="m-4 border border-red-400/40 bg-red-950/20 p-5 text-red-100">
            {apiError}
          </div>
        ) : filteredPapers.length === 0 ? (
          <div className="m-4 border border-dashed border-stone-600 p-5 text-stone-400">
            No matching papers. Try another author, method, or concept.
          </div>
        ) : (
          filteredPapers.map((paper) => (
            <button
              className={classNames("paper-card", activePaperId === paper.id && "active")}
              key={paper.id}
              onClick={() => setActivePaperId(paper.id)}
              type="button"
            >
              <span className={classNames("status-dot", paper.status === "conflict" && "hot")} />
              <strong>{paper.title}</strong>
              <span>{paper.authors}</span>
              <div>
                <small>{paper.year}</small>
                <small className={`tag-${paper.color}`}>{paper.type}</small>
              </div>
            </button>
          ))
        )}
      </div>
    </section>
  );
}

function Stat({ value, label }) {
  return (
    <div className="stat-box">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function IntelligencePanel({
  activePaper,
  activeTab,
  isAsking,
  setActiveTab,
  messages,
  panelData,
  panelStatus,
  prompt,
  setPrompt,
  onSubmit,
  onAction,
  insight
}) {
  return (
    <section className="intelligence-panel flex min-w-0 flex-col bg-[#292925]">
      <div className="tab-row no-scrollbar">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              className={classNames("tab-button", activeTab === tab.id && "active")}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              <Icon size={18} />
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4 md:p-7">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border border-stone-700/80 bg-[#20201c] p-3 text-stone-300">
          <span className="flex items-center gap-2">
            <CheckCircle2 size={18} className="text-emerald-400" />
            {insight}
          </span>
          <span className="text-sm text-stone-500">Active source: {activePaper.authors}, {activePaper.year}</span>
        </div>

        {activeTab === "qa" && <QaPanel messages={messages} activePaper={activePaper} />}
        {activeTab === "review" && (
          <ReviewPanel
            activePaper={activePaper}
            review={panelData.review}
            status={panelStatus.review}
          />
        )}
        {activeTab === "compare" && (
          <ComparePanel
            activePaper={activePaper}
            comparison={panelData.compare}
            conflictsData={panelData.conflicts}
            status={panelStatus.compare || panelStatus.conflicts}
          />
        )}
        {activeTab === "graph" && (
          <GraphPanel
            activePaper={activePaper}
            graph={panelData.graph}
            status={panelStatus.graph}
          />
        )}
      </div>

      <div className="border-t border-stone-700/80 bg-[#252520] p-4">
        <div className="mb-2 grid grid-cols-1 gap-2 sm:grid-cols-4">
          <button className="action-button" onClick={() => onAction("compare")} type="button">
            <GitCompareArrows size={17} />
            Compare papers
          </button>
          <button className="action-button" onClick={() => onAction("conflicts")} type="button">
            <CircleAlert size={17} />
            Find conflicts
          </button>
          <button className="action-button" onClick={() => onAction("review")} type="button">
            <Sparkles size={17} />
            Auto-review
          </button>
          <button className="action-button" onClick={() => onAction("graph")} type="button">
            <Network size={17} />
            Show graph
          </button>
        </div>
        <form className="chat-input" onSubmit={onSubmit}>
          <input
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            disabled={isAsking}
            placeholder={isAsking ? "Asking the corpus..." : "Ask anything about your papers..."}
          />
          <button aria-label="Send question" disabled={isAsking} type="submit">
            <Send size={19} />
          </button>
        </form>
      </div>
    </section>
  );
}

function QaPanel({ messages, activePaper }) {
  const visibleMessages = messages.slice(-3);

  return (
    <div className="qa-panel mx-auto flex max-w-4xl flex-col gap-3">
      {visibleMessages.map((message) => (
        <article className={classNames("message", message.role === "user" ? "user" : "assistant")} key={message.id}>
          <p>{message.body}</p>
          {message.sources.length > 0 && (
            <div className="source-row">
              {message.sources.map((source) => (
                <span key={`${message.id}-${source.paperId}`} title={source.content || source.label}>
                  {source.label} . {source.section} . {source.page}
                </span>
              ))}
            </div>
          )}
        </article>
      ))}

      <RelatedClaims activePaper={activePaper} />
    </div>
  );
}

function RelatedClaims({ activePaper }) {
  return (
    <section className="evidence-box">
      <div className="mb-4 flex items-center justify-between">
        <p className="eyebrow">Related claims across corpus</p>
        <span className="text-sm text-stone-500">{activePaper.confidence.toFixed(2)} confidence</span>
      </div>
      <div className="divide-y divide-stone-700/80">
        {claims.map((claim) => {
          const paper = papers.find((item) => item.id === claim.paperId);
          return (
            <div className="claim-row" key={claim.id}>
              <span className={`claim-dot ${claim.tone}`} />
              <p>
                <strong>{paper?.authors}</strong> - {claim.text}
              </p>
              <ChevronRight size={17} />
            </div>
          );
        })}
      </div>
    </section>
  );
}

function PanelNotice({ status }) {
  if (!status) return null;

  return (
    <div className="mb-4 border border-stone-700/80 bg-[#20201c] p-3 text-stone-300">
      {status === "loading" ? "Loading backend evidence..." : status}
    </div>
  );
}

function ReviewPanel({ activePaper, review, status }) {
  const sections = review?.sections ?? reviewSections.map((section) => ({
    ...section,
    source_count: 0
  }));

  return (
    <div className="mx-auto grid max-w-5xl gap-4 lg:grid-cols-[1fr_0.9fr]">
      <section className="reading-surface">
        <PanelNotice status={status} />
        <p className="eyebrow">Draft literature review</p>
        <h3>{activePaper.type} methods in context</h3>
        {sections.map((section) => (
          <div className="review-block" key={section.id}>
            <h4>{section.title}</h4>
            <p>{section.text}</p>
            <small>{section.source_count} backend source chunk(s)</small>
          </div>
        ))}
      </section>
      <section className="side-surface">
        <p className="eyebrow">Citation checks</p>
        <div className="check-row">
          <CheckCircle2 size={18} />
          Inline APA citations detected
        </div>
        <div className="check-row">
          <CheckCircle2 size={18} />
          Claims mapped to source chunks
        </div>
        <div className="check-row muted">
          <CircleAlert size={18} />
          Head-count efficiency needs another source
        </div>
      </section>
    </div>
  );
}

function ComparePanel({ activePaper, comparison, conflictsData, status }) {
  const comparisonRows = comparison?.rows ?? papers.slice(0, 4).map((paper) => ({
    paper_id: paper.id,
    title: paper.title,
    status: paper.status,
    chunks: paper.citations,
    methodology: paper.title,
    evidence: paper.methodology,
    risk: paper.status === "conflict" ? "Conflicting scaling claim" : "Grounded"
  }));
  const conflictRows = conflictsData?.conflicts ?? conflicts;

  return (
    <div className="mx-auto max-w-6xl">
      <PanelNotice status={status} />
      <div className="compare-grid">
        <div className="compare-head">Paper</div>
        <div className="compare-head">Method</div>
        <div className="compare-head">Key evidence</div>
        <div className="compare-head">Risk</div>
        {comparisonRows.map((paper) => (
          <div className={classNames("compare-row", paper.paper_id === activePaper.id && "selected")} key={paper.paper_id}>
            <strong>{paper.title}</strong>
            <span>{paper.status} . {paper.chunks} chunks</span>
            <p>{paper.evidence}</p>
            <small>{paper.risk}</small>
          </div>
        ))}
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        {conflictRows.map((conflict) => (
          <article className="conflict-card" key={conflict.id}>
            <span>{conflict.severity}</span>
            <h4>{conflict.title}</h4>
            <p>{conflict.detail}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function GraphPanel({ activePaper, graph, status }) {
  const graphNodes = graph?.nodes ?? [
    { id: "active", label: activePaper.type, kind: "paper" },
    { id: "attention", label: "Attention heads", kind: "concept" },
    { id: "methods", label: "Methodology", kind: "concept" },
    { id: "conflicts", label: "Conflicts", kind: "concept" },
    { id: "citations", label: "Citations", kind: "concept" }
  ];

  return (
    <div className="mx-auto grid max-w-5xl gap-5 lg:grid-cols-[1.2fr_0.8fr]">
      <div className="graph-stage">
        <PanelNotice status={status} />
        <span className="node primary">{activePaper.type}</span>
        <span className="node top">Attention heads</span>
        <span className="node left">Methodology</span>
        <span className="node right">Conflicts</span>
        <span className="node bottom">Citations</span>
        <svg viewBox="0 0 600 360" aria-hidden="true">
          <path d="M300 180 L300 64" />
          <path d="M300 180 L126 188" />
          <path d="M300 180 L482 178" />
          <path d="M300 180 L300 298" />
        </svg>
      </div>
      <section className="side-surface">
        <p className="eyebrow">Graph summary</p>
        <h3>{activePaper.title}</h3>
        <p>
          Backend graph loaded {graphNodes.length} node(s), connecting papers, statuses, pages, and source chunks.
        </p>
        <div className="mt-4 divide-y divide-stone-700/80">
          {graphNodes.slice(0, 8).map((node) => (
            <div className="py-2" key={node.id}>
              <strong>{node.label}</strong>
              <span className="ml-2 text-stone-500">{node.kind}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function UploadModal({
  isUploading,
  uploadMode,
  uploadStatus,
  sourceUrl,
  setSourceUrl,
  setUploadMode,
  onClose,
  onSourceUrlSubmit,
  onUploadFile
}) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Upload papers">
      <form className="modal-panel" onSubmit={onSourceUrlSubmit}>
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <p className="eyebrow">Add sources</p>
            <h2 className="mt-1 text-3xl font-medium text-stone-50">Index a paper</h2>
          </div>
          <button className="icon-button" onClick={onClose} type="button" aria-label="Close upload dialog">
            <X size={19} />
          </button>
        </div>
        <div className="upload-mode-row" role="tablist" aria-label="Upload mode">
          {["pdf", "doi", "url"].map((mode) => (
            <button
              className={classNames("upload-mode", uploadMode === mode && "active")}
              key={mode}
              onClick={() => setUploadMode(mode)}
              type="button"
            >
              {mode.toUpperCase()}
            </button>
          ))}
        </div>

        {uploadMode === "pdf" ? (
          <label className="upload-target">
            <input
              accept="application/pdf"
              disabled={isUploading}
              hidden
              type="file"
              onChange={onUploadFile}
            />
            <Upload size={28} />
            <strong>{isUploading ? "Uploading..." : "Choose PDF"}</strong>
            <span>Stored in object storage, then indexed in the background</span>
          </label>
        ) : (
          <div className="upload-target muted">
            <Upload size={28} />
            <strong>{uploadMode === "doi" ? "DOI / arXiv resolver" : "URL resolver"}</strong>
            <span>Direct PDF URLs and arXiv links are supported; publisher DOI pages return a clear backend message.</span>
          </div>
        )}
        {uploadStatus && <p className="upload-status">{uploadStatus}</p>}
        <label className="mt-4 block">
          <span className="mb-2 block text-sm uppercase tracking-[0.16em] text-stone-500">DOI or URL</span>
          <input
            className="modal-input"
            disabled={uploadMode === "pdf"}
            value={sourceUrl}
            onChange={(event) => setSourceUrl(event.target.value)}
            placeholder="10.48550/arXiv.1706.03762"
          />
        </label>
        <button
          className="mt-4 inline-flex w-full items-center justify-center gap-2 bg-violet-500 px-4 py-3 text-lg font-medium text-[#171713]"
          onClick={uploadMode === "pdf" ? onClose : () => {}}
          disabled={isUploading}
          type={uploadMode === "pdf" ? "button" : "submit"}
        >
          {uploadMode === "pdf" ? "Close" : "Queue resolver"}
          <ArrowUpRight size={18} />
        </button>
      </form>
    </div>
  );
}

export default App;
