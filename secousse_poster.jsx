// ============================================================
// SECOUSSE Poster - Font Recreation Script
// Run in Illustrator: File > Scripts > Other Script...
// ============================================================

#target illustrator

// ---- カラー定義 ----
function makeRGB(r, g, b) {
    var c = new RGBColor();
    c.red   = r;
    c.green = g;
    c.blue  = b;
    return c;
}

var BLACK    = makeRGB(0,   0,   0);
var WHITE    = makeRGB(255, 255, 255);
var YELLOW   = makeRGB(255, 220, 0);
var BLUE     = makeRGB(0,   70,  180);
var RED      = makeRGB(200, 20,  20);
var LTBLUE   = makeRGB(180, 210, 240);  // 薄い青（背景帯）
var DARKGRAY = makeRGB(50,  50,  50);

// ---- ドキュメント作成（297 × 500 pt） ----
var W = 297, H = 500;
var doc = app.documents.add(
    DocumentColorSpace.RGB,
    W, H,
    1,
    DocumentArtboardLayout.GridByRow,
    72, 1
);
doc.name = "SECOUSSE_Poster";

var layer = doc.layers[0];
layer.name = "Poster";

// ---- ヘルパー：矩形を描く ----
function addRect(x, y, w, h, fillColor) {
    var r = layer.pathItems.rectangle(y, x, w, h);
    r.filled  = true;
    r.stroked = false;
    r.fillColor = fillColor;
    return r;
}

// ---- ヘルパー：テキストを置く ----
// x,y = 左上基準（Illustratorは左下原点なので変換）
function addText(str, x, y, fontName, size, color, align) {
    var tf = layer.textFrames.add();
    tf.contents = str;
    tf.left   = x;
    tf.top    = H - y;   // 上からの距離 → Illustrator座標

    var ch = tf.textRange.characterAttributes;
    try { ch.textFont = app.textFonts.getByName(fontName); }
    catch(e) {
        // フォールバック
        try { ch.textFont = app.textFonts.getByName("Impact"); }
        catch(e2) {}
    }
    ch.size  = size;
    ch.fillColor = color;

    var para = tf.paragraphs[0].paragraphAttributes;
    if (align === "center") para.justification = Justification.CENTER;
    else if (align === "right") para.justification = Justification.RIGHT;
    else para.justification = Justification.LEFT;

    tf.textRange.autoKernType = AutoKernType.NOAUTOKERN;
    return tf;
}

// ============================================================
// レイアウト構築（上から順に）
// ============================================================

// -- [1] 白背景全体 --
addRect(0, 0, W, H, WHITE);

// --------------------------------------------------------
// ZONE A: ヘッダー（上部 0〜42pt）
// フォント: Impact / Arial Black（極太コンデンス）
// --------------------------------------------------------
addRect(0, 0, W, 42, WHITE);

// "SECOUSSE" : Impact 系, 極太, 大文字
var tSec = addText("SECOUSSE", 8, 8, "Impact", 34, BLACK, "left");
tSec.width = 240;

// ロゴ小文字テキスト（右上の小さいブランドロゴ）
addRect(248, 4, 44, 34, makeRGB(240, 240, 240));
var tLogo = addText("SECOUSSE\nGHETTO MUSIC", 250, 7, "Arial-BoldMT", 5.5, BLACK, "center");
tLogo.width = 40;

// --------------------------------------------------------
// ZONE B: 写真エリア（42〜250pt）- グレープレースホルダー
// --------------------------------------------------------
addRect(0, 42, W, 208, makeRGB(180, 180, 180));

// プレースホルダー文字
var tPhoto = addText("[ 写真エリア ]", 60, 130, "ArialMT", 16, makeRGB(80,80,80), "center");
tPhoto.width = 180;

// --------------------------------------------------------
// ZONE C: 黄色バナー "SPECIAL  AZONTO"（250〜288pt）
// フォント: Times New Roman Bold Italic / serif 系
// --------------------------------------------------------
addRect(0, 250, W, 38, YELLOW);

// 細い黒ライン（上下）
addRect(0, 250, W, 2, BLACK);
addRect(0, 286, W, 2, BLACK);

// "SPECIAL" - 左寄り
var tSp = addText("SPECIAL", 10, 256, "TimesNewRomanPS-BoldItalicMT", 28, BLACK, "left");
tSp.width = 130;

// "AZONTO" - 右寄り
var tAz = addText("AZONTO", 155, 256, "TimesNewRomanPS-BoldItalicMT", 28, BLACK, "left");
tAz.width = 130;

// --------------------------------------------------------
// ZONE D: 情報エリア（288〜460pt）
// 左右に縦線で分割
// --------------------------------------------------------
addRect(0, 288, W, 172, WHITE);

// 縦分割線
addRect(148, 288, 2, 172, BLACK);

// -- 左カラム --
// 薄い青の背景帯（SECOUSSE SOUNDSYSTEM 行）
addRect(0, 288, 148, 40, LTBLUE);

// "SECOUSSE SOUNDSYSTEM"
// フォント: Arial Black / Impact 系, 青
var tSS = addText("SECOUSSE\nSOUNDSYSTEM", 6, 292, "Arial-BoldMT", 13, BLUE, "left");
tSS.width = 138;

// "AND SPECIAL GUESTS"
var tASG = addText("AND SPECIAL\nGUESTS", 6, 335, "ArialMT", 9, BLACK, "left");
tASG.width = 138;

// "DJ BAKO & EZY K"
// フォント: Arial Bold, 青
var tDJ = addText("DJ BAKO & EZY K", 6, 360, "Arial-BoldMT", 13, BLUE, "left");
tDJ.width = 138;

// "(NIGERIA)"
var tNG = addText("(NIGERIA)", 6, 380, "ArialMT", 9, BLACK, "left");
tNG.width = 138;

// -- 右カラム --
// "FAVELA CHIC"
// フォント: Impact / Arial Black 系, 極太
var tFC = addText("FAVELA CHIC", 155, 292, "Impact", 18, BLACK, "left");
tFC.width = 138;

// 細い黒ライン
addRect(150, 322, 145, 1.5, BLACK);

// "17 JUILLET" + "2013"
var tDate1 = addText("17 JUILLET", 155, 326, "Arial-BoldMT", 14, BLACK, "left");
tDate1.width = 138;
var tDate2 = addText("2013", 155, 343, "Arial-BoldMT", 22, BLACK, "left");
tDate2.width = 138;

// "19.00 — 03.00"
addRect(150, 366, 145, 1.5, BLACK);
var tTime = addText("19.00 — 03.00", 155, 370, "Arial-BoldMT", 12, BLACK, "left");
tTime.width = 138;
addRect(150, 385, 145, 1.5, BLACK);

// "ENTRÉE LIBRE" - 赤
var tEL = addText("ENTRÉE\nLIBRE", 155, 390, "Impact", 18, RED, "left");
tEL.width = 138;

// --------------------------------------------------------
// ZONE E: フッター（460〜500pt）
// 黒背景, 白文字, 住所
// --------------------------------------------------------
addRect(0, 460, W, 40, BLACK);

// 縦線（中央）
addRect(148, 460, 1.5, 40, WHITE);

// 左住所
var tAddr1 = addText("60 quai de Jemmapes 10e", 6, 468, "ArialMT", 7, WHITE, "left");
tAddr1.width = 138;

// 右住所
var tAddr2 = addText("18 Rue du Faubourg du Temple 11e", 152, 468, "ArialMT", 7, WHITE, "left");
tAddr2.width = 140;

// --------------------------------------------------------
// 上下の黒ライン（ポスター枠線）
// --------------------------------------------------------
addRect(0, 0, W, 3, BLACK);
addRect(0, 497, W, 3, BLACK);

// ---- 完了 ----
alert(
    "SECOUSSEポスターのフォント再現が完了しました。\n\n" +
    "使用フォント:\n" +
    "  ・Impact             … SECOUSSE / FAVELA CHIC / ENTRÉE LIBRE\n" +
    "  ・TimesNewRomanPS-BoldItalicMT … SPECIAL AZONTO（セリフイタリック）\n" +
    "  ・Arial-BoldMT       … SOUNDSYSTEM / DJ BAKO / 日付\n" +
    "  ・ArialMT            … サブテキスト / 住所\n\n" +
    "写真はリンク配置で差し替えてください。"
);
