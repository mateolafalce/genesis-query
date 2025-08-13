function showToast(message) {
    var toast = document.getElementById("toast");
    toast.innerHTML = message;
    toast.className = "show";
    setTimeout(function(){
        toast.className = toast.className.replace("show", "");
    }, 3000);
}

document.addEventListener("DOMContentLoaded", function() {
    var form = document.getElementById("commentForm");
    if (form) {
        form.addEventListener("submit", function(e) {
            e.preventDefault();
            var formData = new FormData(form);
            fetch("/comentar_ajax", {
                method: "POST",
                body: formData,
                headers: {
                "X-Requested-With": "XMLHttpRequest"
                }
            })
            .then(response => response.json())
            .then(data => {
                showToast(data.message);
                if (data.success) {
                    window.location.href = `/?page=${data.last_page}`;
                }
            });
        });
    }
});

function upvoteAjax(commentId) {
    fetch(`/upvote_ajax/${commentId}`, {
        method: "POST",
        headers: {
            "X-Requested-With": "XMLHttpRequest"
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById(`votes-${commentId}`).textContent = data.votes;
        } else {
            showToast(data.message);
        }
    });
}

function getFlagUrl(code) {
    if (!code || code === "WH") {
        return "https://upload.wikimedia.org/wikipedia/commons/2/2f/Flag_of_White.svg";
    }
    return `https://flagcdn.com/24x18/${code.toLowerCase()}.png`;
}

function countryCodeToEmoji(code) {
    if (!code || code.length !== 2) return "🏳️"; 
        const A = 0x1F1E6;
        return String.fromCodePoint(A + code.toUpperCase().charCodeAt(0) - 65) + String.fromCodePoint(A + code.toUpperCase().charCodeAt(1) - 65);
}
