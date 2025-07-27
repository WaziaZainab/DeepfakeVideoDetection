document.addEventListener("DOMContentLoaded", () => {
    const fileInput = document.getElementById("fileInput");
    const browseBtn = document.getElementById("browseBtn");
    const analyzeBtn = document.getElementById("analyzeBtn");
    const dropzone = document.getElementById("dropzone");
    const videoPreview = document.getElementById("videoPreview");
    const previewContainer = document.getElementById("previewContainer");
    const progressWrap = document.getElementById("progressWrap");
    const progressBar = document.getElementById("progressBar");
    const progressText = document.getElementById("progressText");
    const resultCard = document.getElementById("resultCard");
    const predictionBadge = document.getElementById("predictionBadge");
    const confidenceText = document.getElementById("confidenceText");
    const timeText = document.getElementById("timeText");

    let selectedFile = null;

    browseBtn.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            selectedFile = e.target.files[0];
            analyzeBtn.disabled = false;
            showVideoPreview(selectedFile);
        }
    });

    dropzone.addEventListener("dragover", (e) => e.preventDefault());
    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        selectedFile = e.dataTransfer.files[0];
        analyzeBtn.disabled = false;
        showVideoPreview(selectedFile);
    });

    analyzeBtn.addEventListener("click", () => {
        if (!selectedFile) return;
        uploadVideo(selectedFile);
    });

    function showVideoPreview(file) {
        const url = URL.createObjectURL(file);
        videoPreview.src = url;
        previewContainer.style.display = "block";
    }

    function uploadVideo(file) {
        const formData = new FormData();
        formData.append("video", file);
        progressWrap.style.display = "block";
        progressBar.style.width = "0%";
        progressText.innerText = "0%";
        fetch("/predict", { method: "POST", body: formData })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert("Error: " + data.error);
                return;
            }
            resultCard.style.display = "block";
            predictionBadge.innerText = data.label;
            confidenceText.innerText = (data.confidence * 100).toFixed(2) + "%";
            timeText.innerText = data.inference_time;
            loadHistory();
        }).catch(err => {
            console.error(err);
            alert("Prediction failed.");
        });
    }

    function loadHistory() {
        fetch("/api/history")
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById("historyBody");
            tbody.innerHTML = "";
            data.history.forEach((h, idx) => {
                tbody.innerHTML += `
                    <tr>
                        <td>${idx + 1}</td>
                        <td>${h.filename}</td>
                        <td>${h.label}</td>
                        <td>${(h.confidence * 100).toFixed(2)}%</td>
                        <td>${h.created_at}</td>
                    </tr>`;
            });
            document.getElementById("historyCard").style.display = "block";
        });
    }
});
