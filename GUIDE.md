# Taste Agent — chalane aur test karne ki guide

## 1. App chalana

Do cheezein chalni chahiyein. Do alag terminal kholein.

**Terminal 1 — backend:**

```bash
cd D:\Qloo\backend && ..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

**Terminal 2 — frontend:**

```bash
cd D:\Qloo\frontend && node node_modules/vite/bin/vite.js --port 5173
```

Phir browser mein kholein: **http://localhost:5173**

Upar right mein do badge hone chahiyein — `Qloo live` aur `groq`. Dono hare hon to sab theek hai.

---

## 2. Folder mein kya kya hai

```
D:\Qloo\
├── backend\app\
│   ├── config.py          keys parhta hai, mode chunta hai
│   ├── main.py            FastAPI app
│   ├── qloo\              QLOO KA SAARA KAAM
│   │   ├── client.py        asli Qloo API calls
│   │   ├── mock.py          nakli data (net na ho to)
│   │   ├── models.py        Entity aur Tag ki shape
│   │   └── entity_types.py  13 types, 4 pillars
│   ├── agent\             AGENT KA DIMAAG
│   │   ├── tools.py         4 tools jo agent use karta hai
│   │   ├── groq_brain.py    Groq se baat
│   │   ├── brain.py         Claude se baat (key ho to)
│   │   ├── planner.py       bina LLM ke backup dimaag
│   │   └── taste_read.py    taste signature
│   ├── storage\           session JSON mein save
│   └── routers\           /api/chat, /api/sessions, /api/qloo
├── frontend\src\
│   ├── App.jsx            poori app
│   └── components\        chat, cards, sidebar
├── data\sessions\         har session ek JSON file
├── docs\                  Qloo API ki research
├── PROGRESS.md            har stage ka record
└── GUIDE.md               yeh file
```

---

## 3. Pillars green kaise hote hain

### Asool

> Pillar sirf tab green hota hai jab **AAP** koi cheez pasand batayein.
> Agent jo recommend kare, us se green **nahi** hota.

Yeh jaan boojh kar aisa hai. Pillar ka matlab hai "is banday ki taste ka mujhe is domain mein pata hai" — agent ka andaza aapki taste nahi banta.

### Chaar pillars, aur har ek ke liye kya kehna hai

| Pillar | Kya kehna hai | Kya banta hai |
|---|---|---|
| **Entertainment** | `I love Blade Runner 2049` | Movie |
| | `Severance` | TV Show / Book |
| | `Radiohead` | Artist |
| | `Death Stranding` | Video Game |
| **Fashion & Brands** | `I love MUJI` | Brand |
| | `Acne Studios` | Brand |
| | `Nike` | Brand |
| **People & Culture** | `Haruki Murakami` | Author |
| | `Virgil Abloh` | Person |
| **Lifestyle & Travel** | `Blue Bottle Coffee` | Place |

Chaaron test kiye, chaaron green hote hain.

### Aap shayad kyun sirf do dekh rahe thay

Aap ne films, shows aur music ka naam liya — wo sab **Entertainment** hai. Phir "Berlin" kaha — wo location ban gaya (sidebar mein "Anchored in"), signal nahi.

Brands aur logon ka naam lein to baaki do bhi green ho jayenge.

### Demo ke liye poora script

Yeh char jumle bolein, chaaron pillars green ho jayenge:

```
1.  I love Blade Runner 2049 and Severance
2.  I also like MUJI and Acne Studios
3.  Haruki Murakami is my favourite writer
4.  Blue Bottle Coffee is my kind of place
```

Phir sidebar mein **Taste Read** dekhein — `Isolation · Dystopian · Thoughtful · Fiction`.
Yeh chaaron pillars se nikla hua aapki taste ka signature hai.

### Chhote akhar bhi chalte hain

`i love muji and acne studios` — bilkul theek hai. Bare akhar zaroori nahi.

---

## 4. Images

Cards par tasveerein Qloo se aati hain. Maine har type check kiya:

| Type | Images |
|---|---|
| Movie, TV Show, Book, Brand, Artist, Person, Podcast, Place | **har result par** |
| Video Game | kuch par (8 mein se 3) |

Jahan image na ho, card par naam ka pehla harf dikhta hai — khali dabba nahi.

---

## 5. Test kaise karein

### Sabse chhota test (30 second)

1. `New session` dabayein
2. Likhein: `I love Blade Runner 2049 and MUJI`
3. Likhein: `I'm in Berlin`
4. Cards aane chahiyein — tasveer, address, `80% match`, tags

### Cross-domain test — yahi asli cheez hai

Film se seedha cafe tak:

```
I love Blade Runner 2049    →  film
I'm in Tokyo                 →  shehar
Where should I eat?          →  Tokyo ke restaurants
What brand would suit me?    →  Tesla, Apple, Sony
```

Ek film se **teen alag domains** nikal aaye. Yeh dikhana demo mein sabse zaroori hai.

### Sidebar ke buttons

- **Pillar par click** → us domain ka sawal khud chala jata hai
- **Card par ×** → wo cheez dobara kabhi nahi aayegi
- **Signal par ×** → wo pasand profile se hat jati hai
- **Profile button** (chhoti screen par) → sidebar drawer khulta hai

### Mock mode test (net ke baghair)

`.env` mein `QLOO_MOCK_MODE=1` kar dein aur backend dobara chalayein. Badge `Qloo mock` ho jayega, app phir bhi chalegi. Demo ke din net gir jaye to yeh bachata hai.

---

## 6. Agar kuch na chale

| Masla | Hal |
|---|---|
| Badge `rules` dikh raha hai | Groq key `.env` mein nahi hai, ya purani key system environment mein pari hai |
| Jawab aane mein 20 second | Normal hai — agent Qloo ko call karta hai, phir sochta hai |
| `Backend unreachable` | Terminal 1 band ho gaya, dobara chalayein |
| Port 8000 pehle se liya hua | Purana server chal raha hai, usay band karein |

---

## 7. Jaanne ki baatein

**Ek hi naam ki do cheezein.** "Severance" ek novel bhi hai aur show bhi, aur Qloo dono ko barabar rakhta hai. Agar aap sirf `severance` likhein to agent khud pin karta hai; aap `the show severance` ya `the novel severance` likh kar bhi bata sakte hain.

**Qloo ke teen entity types tootay huay hain** is hackathon API par — `director` bilkul kaam nahi karta, `author` aur `locality` sirf search mein chalte hain. Maine inhein agent se hata diya hai taake wo bekaar call na kare. Directors ab `person` ke zariye milte hain.
