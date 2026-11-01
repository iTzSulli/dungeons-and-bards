# Dungeon & Bard

Gioco fantasy desktop per Windows: prepara un'avventura, crea da uno a tre personaggi e affronta scene narrative con prove D20. L'interfaccia e il gioco sono in italiano e inglese. Il regolamento è leggero e non sostituisce le regole complete di D&D 2024.

## Installare e avviare

Scarica `DungeonAndBardSetup.exe` dalla cartella `dist` ed eseguilo. L'installer:

- installa il gioco per l'utente corrente senza richiedere privilegi amministrativi;
- crea un collegamento nel menu Start e offre facoltativamente quello sul desktop;
- permette di avviare il gioco al termine dell'installazione e installa un programma di disinstallazione;
- lascia intatte le impostazioni personali conservate in `%LOCALAPPDATA%\DungeonAndBard` quando il gioco viene disinstallato.

L'eseguibile portatile `dist\DungeonAndBardGame.exe` puo anche essere avviato direttamente, senza installazione.

## Preparare la partita

La creazione si svolge in due passaggi. Nella prima pagina scegli il numero di giocatori (da uno a tre), la durata, la difficolta e l'ambientazione; il D6 combina uno fra 18 luoghi, 18 fenomeni e 18 minacce. Puoi aggiungere un dettaglio facoltativo. Nella pagina dei personaggi scegli nome, specie e classe per ciascun giocatore e distribuisci i 27 punti point buy sulle sei caratteristiche (valori da 8 a 15). Il gioco calcola modificatori e punti ferita iniziali. Ogni classe mostra uno spunto narrativo: aiuta il narratore a coinvolgere il personaggio nella fiction, ma non è una capacità regolistica né aggiunge bonus ai tiri. Le specie seguono l'impostazione 2024 e non assegnano bonus automatici alle caratteristiche. Durante la creazione, nelle impostazioni e nell'avventura, puoi premere Esc o selezionare **INDIETRO** per tornare alla schermata precedente; dal menu principale Esc apre la conferma di uscita.

## Giocare

La partita si svolge in una chat libera: non ci sono sequenze obbligatorie di ostacoli né un finale imposto dal timer. Con il Worker Cloudflare collegato, puoi descrivere qualsiasi azione; il narratore valuta se è automatica, impossibile nella situazione o abbastanza incerta da richiedere una prova, scegliendo personaggio, caratteristica e CD. Il gioco tira localmente il D20, applica modificatori e competenze e mostra il risultato in un riquadro animato: il punteggio della caratteristica determina il modificatore (per esempio Saggezza 12 dà +1), la competenza aggiunge +2 e la somma è il bonus applicato al D20. Un fallimento nelle prove di osservazione può limitare la certezza o introdurre una complicazione, ma non dovrebbe cancellare ogni dettaglio della scena. Se un attacco va a segno, il narratore può richiedere anche un dado danni da D4 a D12, tirato separatamente dal D20. L'IA racconta le conseguenze senza poter cambiare il tiro. Ogni risposta reagisce alla mossa appena descritta e invita a proseguire con una domanda aperta, senza imporre una strada. In gruppi con più personaggi il turno passa automaticamente al successivo dopo ogni azione e il nome di chi agisce è mostrato sopra la chat e nel messaggio. La durata è un'indicazione di ritmo, non una condizione di fine. Senza il Worker, le risposte locali sono più semplici e non possono improvvisare dettagli specifici con la stessa qualità del narratore AI.

La voce narrante parte automaticamente all'avvio dell'avventura e dopo ogni risposta; **MUTA VOCE** la interrompe e la disattiva, mentre **RIATTIVA VOCE** la riattiva e legge la risposta corrente. Per partire più rapidamente, la voce consigliata è una voce di sistema Windows installata sul PC. Nelle impostazioni puoi scegliere anche Isabella, Elsa o Diego in italiano e Aria, Sonia o Guy in inglese: le voci neurali online possono richiedere più tempo e inviano il testo a Microsoft per la sintesi.

La sintesi online usa la libreria open source [edge-tts](https://github.com/rany2/edge-tts), che accede al servizio vocale online di Edge senza una API ufficiale dedicata: la disponibilita e la gratuitita non sono garantite da un contratto di servizio e Microsoft puo cambiare o limitare l'accesso. L'app non invia la voce sintetizzata al narratore AI di Cloudflare.

## Narratore AI facoltativo

Puoi collegare il gioco a un tuo Cloudflare Worker con Workers AI. Il modello interpreta l'azione libera e propone l'eventuale prova; il gioco verifica il personaggio e le caratteristiche, tira i dadi e applica il risultato. L'IA non può modificare i risultati dei dadi. Senza configurazione il gioco resta utilizzabile con una valutazione locale più limitata.

### Pubblicare il Worker

Prerequisiti: un account Cloudflare con Workers AI abilitato, Node.js 22 o successivo e npm.

1. Apri PowerShell nella cartella principale del progetto ed entra nella cartella del Worker:

   ```powershell
   cd .\cloudflare
   ```

   Installa quindi gli strumenti del Worker e collega Wrangler al tuo account Cloudflare:

   ```powershell
   npm install
   npx wrangler login
   ```

   Il comando di accesso apre una pagina nel browser: accedi a Cloudflare e autorizza Wrangler.

2. Crea una password casuale che userai per collegare il gioco al Worker. Esegui il comando e conserva il valore stampato:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. Registra quel valore come segreto Cloudflare. Quando Wrangler lo chiede, incolla il token generato al passaggio precedente:

   ```powershell
   npx wrangler secret put NARRATOR_ACCESS_TOKEN
   ```

4. In `wrangler.jsonc`, cambia `namespace_id` solo se `1001` e gia usato da un altro Worker del tuo account; deve essere un identificatore numerico univoco. Pubblica il Worker:

   ```powershell
   npm run deploy
   ```

   Al termine Wrangler mostra l'indirizzo pubblico del Worker, simile a `https://dungeon-bard-narrator.nome-account.workers.dev`. Puoi verificare che sia online aprendo quell'indirizzo nel browser: deve rispondere `{"service":"Dungeon & Bard narrator","status":"ok"}`.

5. Avvia Dungeon & Bard e apri **Impostazioni** > **Narratore AI** > **Imposta**. Nel campo URL inserisci l'indirizzo mostrato da Wrangler, senza aggiungere `/narrate`; nel campo token inserisci lo stesso valore salvato al passaggio 3. Puoi incollare con **Ctrl+V**; il campo token lo nasconde. Premi **SALVA**.

Per pubblicare il nuovo comportamento del narratore, dalla cartella principale esegui `cd .\cloudflare` e poi `npm run deploy`. Per distribuire anche gli aggiornamenti dell'app, esegui `.\package.ps1` dalla cartella principale del progetto; le modifiche successive al solo Worker non richiedono di ricreare l'eseguibile.

Il Worker usa il modello Cloudflare `@cf/meta/llama-3.3-70b-instruct-fp8-fast` e un limite approssimativo di 8 richieste al minuto per indirizzo IP. Un'azione normalmente richiede due richieste (valutazione del narratore e successiva narrazione), quindi il limite consente circa 4 azioni al minuto. Quote, disponibilita, prezzi e condizioni possono cambiare: consulta la [documentazione Workers AI](https://developers.cloudflare.com/workers-ai/) e i [prezzi](https://developers.cloudflare.com/workers-ai/platform/pricing/).

Per generare la narrazione vengono inviati a Cloudflare ambientazione, nomi, classi, caratteristiche e competenze dei personaggi, azioni, decisioni sulle prove, risultati dei tiri e una parte della cronologia. Non inserire dati personali. Il token del Worker viene salvato in `%LOCALAPPDATA%\DungeonAndBard\settings.json` e non e incluso nell'eseguibile; chi puo leggere il file locale puo recuperarlo. Se distribuisci il gioco ad altre persone, fai configurare a ciascuno un proprio Worker e token. La voce narrante resta locale e non viene inviata a Cloudflare.

## Sviluppo e build Windows

Per avviare il codice sorgente, installa Python 3.10 o successivo e le dipendenze, inclusa la libreria per la voce neurale online:

```powershell
python -m pip install -r requirements-build.txt
python game.py
```

Per creare il solo eseguibile portatile:

```powershell
.\build.ps1
```

Per creare l'eseguibile e il setup installabile, installa [Inno Setup 6](https://jrsoftware.org/isinfo.php), quindi esegui dalla cartella del progetto:

```powershell
winget install --id JRSoftware.InnoSetup --exact
.\package.ps1
```

`package.ps1` produce `dist\DungeonAndBardGame.exe` e `dist\DungeonAndBardSetup.exe`. Il setup e destinato a Windows a 64 bit. Per verificare il Worker dopo aver installato le dipendenze npm:

```powershell
cd cloudflare
npm test
```
