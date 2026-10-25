import { createRoot } from "react-dom/client";
import { App } from "./App";
import { Player } from "./player";
import "./styles.css";

const audio = document.createElement("audio");
audio.id = "side-a-audio";
audio.hidden = true;
document.body.append(audio);
const player = new Player(audio, {
  getItem: (key) => window.localStorage.getItem(key),
  setItem: (key, value) => window.localStorage.setItem(key, value),
  removeItem: (key) => window.localStorage.removeItem(key),
});
window.addEventListener("pagehide", player.persist);
createRoot(document.getElementById("root")!).render(<App player={player} />);
