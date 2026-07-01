const API_BASE_URL = 
    import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, options);

    if(!response.ok) {
        let message = `Request failed with status ${response.status}`;

        try {
            const data = await response.json();
            message = data.detail || data.message || message;
        } catch (error) {
            // Ignore JSON parsing errors and use the default message
        }

        throw new Error(message);
    }

    return response.json();
}

export function getPapers() {
    return request("/papers");
}

export function getPaperStatus(paperID) {
    return request(`/papers/${paperID}/status`);
}

export function askQuestion({ question, paperID }) {
    return request("/ask",{
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ 
            question,
            paper_id: paperID
        }),
    });
}

export function uploadPaper(file) {
    const formData = new FormData();
    formData.append("file", file);

    return request("/upload", {
        method: "POST",
        body: formData,
    });
}