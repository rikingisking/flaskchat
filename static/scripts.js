document.addEventListener("DOMContentLoaded", function() {
    const form = document.querySelector("form");
    const textarea = document.querySelector("textarea");

    form.addEventListener("submit", function(event) {
        if (textarea.value.trim() === "") {
            event.preventDefault();
            alert("テキストを入力してください。");
        }
    });
});
