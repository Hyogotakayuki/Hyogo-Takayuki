//kigo
console.log(3-2);        //出力結果｝1
console.log(15/3*5+5-15);//出力結果｝15
let text="さんおはようございます";
console.log("佐藤"+text);
  //出力結果｝佐藤さんおはようございます
console.log("鈴木"+text);
  //出力結果｝鈴木さんおはようございます
console.log("田中"+text);
  //出力結果｝田中さんおはようございます
console.log("鈴森"+text);
  //出力結果｝鈴森さんおはようございます

 　 //変数の更新
let number0 = 7;

number0 = number0 + 9;

console.log(number0);  //出力結果｝16

　　//【変数の値更新の省略形式】
let number = 7;
console.log(number);    //出力結果｝7
// 変数numberの値に3を加えてください
number += 3;
console.log(number);    //出力結果｝10
// 変数numberの値を2で割ってくださ
number /= 2;
console.log(number);    //出力結果｝5

const number1 = 12;
    //大小比較演算子
    console.log(number1 < 13);    //出力結果｝true
    console.log(number1 > 11);    //出力結果｝true
    console.log(number1 <= 12);   //出力結果｝true
    console.log(number1 >= 12);   //出力結果｝true
    //等価演算子
    console.log(number1 == 12);   //出力結果｝true
    console.log(number1 == "12"); //出力結果｝true
    console.log(number1 != 13);   //出力結果｝true
    console.log(number1 != "13"); //出力結果｝true
    //厳密等価演算子
    console.log(number1 === 12);  //出力結果｝true
    console.log(number1 !== 11);  //出力結果｝true
    console.log(number1 !== "12");//出力結果｝true
    console.log(number1 === "12");//出力結果｝false
    //passwordが”ninjawanko"で合っている場合”ログインに成功”と表示
const password = "ninjawanko";

    // passwordの値が"ninjawanko"の場合、「ログインに成功しました」と出力してください
if (password === "ninjawanko") {
      console.log("ログインに成功しました");
}       //出力結果｝ログインに成功しました

    // passwordの値が"ninjawanko"でない場合、「パスワードが間違っています」と出力してください
if (password !== "ninjawank") {
      console.log("パスワードが間違っています");
}       //出力結果｝パスワードが間違っています

const age = 24;
// 「age >= 20」を出力してください
console.log(age >= 20);         //出力結果｝true
// 「age < 20」を出力してください
console.log(age < 20);          //出力結果｝false
// ageの値が20以上の場合に、「私は20歳以上です」と出力してください
if (age >= 20) {
  console.log("私は20歳以上です");//出力結果｝私は20歳以上です
}

const age1 = 13;
if (age1 >= 20) {
  　console.log("私は20歳以上です");
  
} else {
 　 console.log("私は20歳未満です");
}     //出力結果｝私は20歳未満です

//const age = 17;
    // ageの値が10以上20未満のとき、「私は20歳未満ですが、10歳以上です」と出力してください
if (age >= 20) {
      console.log("私は20歳以上です");
} else if (age >= 10) {
      console.log("私は20歳未満ですが、10歳以上です");
} else {
      console.log("私は10歳未満です");
}       //出力結果｝私は20歳未満ですが、10歳以上です
    
const name0 = "にんじゃわんこ";
const age0 = 14;
console.log(`${name0}は、${age0}歳です。`);

const fruits = 'apple';

switch (fruits) {
  case 'banana':
    console.log('バナナです！');
    break;
  case 'orange':
    console.log('オレンジです！');
    break;
  case 'mango':
    console.log('マンゴーです！');
    break;
  default:
    console.log('一致するフルーツがありません。');
    // どのcaseにも一致しない場合に実行されます。
}     //出力結果｝一致するフルーツがありません。

const signal = "red";

switch (signal) {
  case "red":
    console.log("赤");
    break;
  case "green":
    console.log("緑");
    break;
  case "blue":
    console.log("青");
    break;
  default:
    console.log("該当なし")

}        //出力結果｝赤

// 変数numberを定義してください
let numbr2 = 0;

// 変数numberに1を加えて、その後に変数numberの値を出力してください
//numbr += 1;
console.log(numbr2);
//出力結果｝1
// 上述の2行のコードを4回、貼り付けてください
numbr2 += 1;
console.log(numbr2);
//出力結果｝2
numbr2 += 1;
console.log(numbr2);
//出力結果｝3
numbr2 += 1;
console.log(numbr2);
//出力結果｝4
numbr2 += 1;
console.log(numbr2);
//出力結果｝5

// 変数numberを定義してください
//let number = 1;
// while文を作成してください
//while (number <= 100) {
  //console.log(number);
  //number += 1;
//}//出力結果｝1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20

for (let number3 = 1; number3 <= 100; number3++) {
  console.log(number3);
}//出力結果｝1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20

// for文を完成させてください
for (let number4 = 1; number4 <= 100; number4++) {
  // if文を用いて、numberが3の倍数の時に「3の倍数です」、そうでないときは数字を出力してください
  if (number4 % 3 === 0) {
    console.log("3の倍数です");
  } else {
    console.log(number4);
  }
}//出力結果｝1 2 3の倍数です 4 5 3の倍数です 7 8 3の倍数です 10

　　　　　　　　　　　　//配列
//    定数animalsに、指定された配列を代入してください
const animals = ["dog", "cat", "sheep", "rabbit",
   "monkey", "tiger", "bear", "elephant"];
//    lengthを用いて配列の要素の数を出力してください
console.log(animals.length);
//dog", "cat", "sheep", "rabbit","monkey", "tiger",
// "bear", "elephant"
//     lengthを用いて条件式を書き換えてください
for (let i = 0; i < animals.length; i++) {
}//出力結果｝　8
// 定数animalsを出力して下さい
console.log(animals);
// 配列の1つ目の要素を出力してください
console.log(animals[0]);
//出力結果｝dog
// 配列の3つ目の要素を出力してください
console.log(animals[2]);
//出力結果｝cat
// 配列animalsの3つ目の要素を「rabbit」に更新してください
animals[2] = "rabbit";
// 配列animalsの3つ目の要素をコンソールに表示して下さい
console.log(animals[2]);
//出力結果｝rabbit

　　　　　　//length連なりレングス
// lengthを用いて配列の要素の数を出力してください
console.log(animals.length);
// lengthを用いて条件式を書き換えてください
for (let i = 0; i < animals.length; i++) {
  console.log(animals[i]);
}

　　　　　　　　//オブジェクト
//定数characterを定義し、以下の2つの要素を持つオブジェクトを代入してください。
//1つ目の要素 プロパティ名：name 値：にんじゃわんこ
//2つ目の要素プロパティ名：age 値：14
//定数characterの値をコンソールに出力してください。
// 定数characterを定義し、指定されたオブジェクトを代入してください
const characters = {name: "にんじゃわんこ", age: 14};
//　　　　↑　　　　 　↑         　↑　　      ↑    ↑
//      定数    プロパティ　　　 数値　プロパティ 数値
//characterの値を出力してください
console.log(characters);
//            定数
//出力結果｝　　　　　　結果
//{name: 'にんじゃわんこ',age: 14}
//age:14
//name:"にんじゃわんこ"

　　　　　　　//オブジェクトの値と紐づける
const item = {name: "手裏剣", price: 300};
item.price = 500;
console.log(item.price);
console.log(item);
//出力結果｝
//500
//{name: '手裏剣', price: 500}
//name: "手裏剣"
//price:500
　　　　　　　　　//オブジェクトを配列にする
const items = [
  {name: "手裏剣", price: 300},
  {name: "忍者刀", price: 1200}
];
const characters1 = [
  {name: "にんじゃわんこ", age: 14},
  {name: "ひつじ仙人", age: 1000}
];
// charactersの1つ目の要素をコンソールに出力してください
console.log(characters1[0]);
// charactersの2つ目の要素の「name」に対応する値をコンソールに出力してください
console.log(characters1[1].name);
//出力結果｝
//{name: 'にんじゃわんこ', age: 14}
//age:14
//name:"にんじゃわんこ"
const characters2 = [
  {name: "にんじゃわんこ", age: 14},
  {name: "ひつじ仙人", age: 100},
  {name: "ベイビーわんこ", age: 5},
];

// for文を完成させてください
for (let i = 0; i < characters.length; i++) {
  console.log("--------------------");
  
  // 定数characterを定義してください
  const character = characters[i];
  
  // 「名前は〇〇です」を出力してください
  console.log(`名前は${characters.name}です`);
  
  // 「〇〇歳です」を出力してください
  console.log(`${characters.age}歳です`);
  
}

