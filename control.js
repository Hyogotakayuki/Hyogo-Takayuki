//DOMを掴む
const who1 = document.getElementById("who");
const doing1 = document.getElementById("doing");
const feedBack = document.getElementById("feedBack");

//事で困ることは？につなげる
const who2 = document.getElementById("who2");

//感情ボタン
const btnAnxiety = document.getElementById("anxiety");
const btnDissatisfaction = document.getElementById("dissatisfaction");
const btnAnger = document.getElementById("anger");

//記憶する箱を作る---(オブジェクト)---
let memory = null;
// 例：{ who:"上司", doing:"怒鳴っている", emotion:"不安" }

// ======共通処理：感情が選ばれた時に保存＆表示======
function saveAndShow(emotionText) {
    const whoText = who1.value.trim();
    const doingText = doing1.value.trim();
    
    //入力チェック
    if (!whoText || !doingText) {
        feedBack.textContent = "「誰」が、「どうしている？」を入力してください。";
        return;
    }

// 記憶する
memory = { who: whoText, doing: doingText, emotion: emotionText };

// 表示する
feedBack.textContent = `${memory.who}が${memory.doing}ことに「${memory.emotion}」を感じた事で困ることは？`;

// 次へつなぐ（困ることは？側へフォーカス移動）
who2.focus();
}

// ======ボタンにクリックイベントを付ける ======
anxiety.addEventListener("click", function(){
    saveAndShow("不安");
});
dissatisfaction.addEventListener("click", function(){
    saveAndShow("不満");
});
btnAnger.addEventListener("click", function(){
    saveAndShow("怒り");
});

