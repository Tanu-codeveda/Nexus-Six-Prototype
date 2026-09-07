import React, { useEffect, useRef, useState } from 'react';

const RANCHI = { latitude: 23.3441, longitude: 85.3096 };
const API_BASE = `${window.location.protocol}//${window.location.hostname}:8000`;
const STORAGE_KEY = 'civicpulse.myReportIds';

const EMPTY_COMPLAINT = {
  id: null,
  ...RANCHI,
  media_url: null,
  description: '',
  voice_transcript: '',
  ai_category: 'Not analyzed',
  ai_severity: 'Not analyzed',
  ai_confidence_score: null,
  status: 'Pending',
  assigned_department: 'Pending AI analysis',
};

const readStoredReportIds = () => {
  try {
    const ids = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    return Array.isArray(ids) ? ids : [];
  } catch {
    return [];
  }
};

const rememberReportId = (id) => {
  if (!id) return;
  try {
    const ids = readStoredReportIds().filter((value) => value !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify([id, ...ids].slice(0, 50)));
  } catch {
    // LocalStorage is optional for the prototype.
  }
};

const hasReportContent = (description, photo, voiceDataUrl) =>
  Boolean((description || '').trim() || photo || voiceDataUrl);

const Icon = ({ name, size = 20 }) => {
  const p = {
    stroke: 'currentColor',
    strokeWidth: 2,
    fill: 'none',
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
  };
  const paths = {
    home: <><path {...p} d="m3 10 9-7 9 7" /><path {...p} d="M5 9v11h14V9" /><path {...p} d="M9 20v-6h6v6" /></>,
    plus: <><path {...p} d="M12 5v14M5 12h14" /></>,
    file: <><path {...p} d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path {...p} d="M14 2v6h6M8 13h8M8 17h6" /></>,
    user: <><circle {...p} cx="12" cy="8" r="3" /><path {...p} d="M5 20c.7-3.3 3-5 7-5s6.3 1.7 7 5" /></>,
    pin: <><path {...p} d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z" /><circle {...p} cx="12" cy="10" r="2.5" /></>,
    camera: <><path {...p} d="M4 7h3l1.5-2h7L17 7h3v12H4z" /><circle {...p} cx="12" cy="13" r="3.5" /></>,
    mic: <><rect {...p} x="9" y="3" width="6" height="11" rx="3" /><path {...p} d="M6 11a6 6 0 0 0 12 0M12 17v4M9 21h6" /></>,
    spark: <><path {...p} d="m12 3 1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6z" /><path {...p} d="m19 16 .7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7z" /></>,
    check: <><path {...p} d="m5 12 4 4L19 6" /></>,
    arrow: <><path {...p} d="M5 12h14M13 6l6 6-6 6" /></>,
    back: <><path {...p} d="M19 12H5M11 6l-6 6 6 6" /></>,
    play: <><path fill="currentColor" stroke="none" d="m8 5 11 7-11 7z" /></>,
    info: <><circle {...p} cx="12" cy="12" r="9" /><path {...p} d="M12 10v6M12 7h.01" /></>,
    bell: <><path {...p} d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></>,
    phone: <><path {...p} d="M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.12.9.33 1.78.62 2.63a2 2 0 0 1-.45 2.11L8 9.73a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.85.29 1.73.5 2.63.62A2 2 0 0 1 22 16.92Z" /></>,
    edit: <><path {...p} d="M12 20h9" /><path {...p} d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4z" /></>,
    refresh: <><path {...p} d="M20 11a8 8 0 0 0-14.8-4L3 10" /><path {...p} d="M3 5v5h5M4 13a8 8 0 0 0 14.8 4L21 14" /><path {...p} d="M21 19v-5h-5" /></>,
    globe: <><circle {...p} cx="12" cy="12" r="9" /><path {...p} d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" /></>,
    clock: <><circle {...p} cx="12" cy="12" r="9" /><path {...p} d="M12 7v5l3 2" /></>,
    message: <><path {...p} d="M4 5h16v11H8l-4 4z" /><path {...p} d="M8 9h8M8 12h5" /></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24">{paths[name] || paths.info}</svg>;
};

function App() {
  const [screen, setScreen] = useState('login');
  const [complaint, setComplaint] = useState({ ...EMPTY_COMPLAINT });
  const [writtenDescription, setWrittenDescription] = useState('');
  const [voiceTranscript, setVoiceTranscript] = useState('');
  const [photo, setPhoto] = useState(null);
  const [voiceUrl, setVoiceUrl] = useState(null);
  const [voiceDataUrl, setVoiceDataUrl] = useState(null);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [locationState, setLocationState] = useState('ready');
  const [aiProgress, setAiProgress] = useState(0);
  const [aiError, setAiError] = useState('');
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState('');
  const [lang, setLang] = useState('English');
  const [theme, setTheme] = useState(localStorage.getItem('civicpulse.theme') || 'light');
  const [reportResetKey, setReportResetKey] = useState(0);
  const recorder = useRef(null);
  const timer = useRef(null);
  const recordingStartedAt = useRef(0);
  const toastTimer = useRef(null);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('civicpulse.theme', theme);
  }, [theme]);

  useEffect(() => {
    const openHelplines = () => setModal('helplines');
    window.addEventListener('civicpulse:open-helplines', openHelplines);
    return () => window.removeEventListener('civicpulse:open-helplines', openHelplines);
  }, []);

  const showToast = (message) => {
    setToast(message);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(''), 2800);
  };

  const getLocation = () => {
    setLocationState('loading');
    if (!navigator.geolocation) {
      setComplaint((current) => ({ ...current, ...RANCHI }));
      setLocationState('demo');
      showToast('Location unavailable — using Ranchi demo location');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setComplaint((current) => ({
          ...current,
          latitude: Number(position.coords.latitude.toFixed(6)),
          longitude: Number(position.coords.longitude.toFixed(6)),
        }));
        setLocationState('ready');
      },
      (error) => {
        console.warn('Geolocation failed:', error?.message || error);
        setComplaint((current) => ({ ...current, ...RANCHI }));
        setLocationState('demo');
        showToast(
          error?.code === 1
            ? 'Location permission denied — using Ranchi demo location'
            : 'Could not detect location — using Ranchi demo location'
        );
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
    );
  };

  useEffect(() => {
    if (screen === 'report') getLocation();
  }, [screen]);

  useEffect(() => () => {
    clearInterval(timer.current);
    clearTimeout(toastTimer.current);
    if (recorder.current?.stream) {
      recorder.current.stream.getTracks().forEach((track) => track.stop());
    }
  }, []);

  const handlePhoto = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const previewUrl = URL.createObjectURL(file);
    setPhoto(previewUrl);
    const reader = new FileReader();
    reader.onload = () => {
      setComplaint((current) => ({ ...current, media_url: String(reader.result || '') }));
      showToast('Photo added');
    };
    reader.onerror = () => {
      URL.revokeObjectURL(previewUrl);
      setPhoto(null);
      setComplaint((current) => ({ ...current, media_url: null }));
      showToast('Could not read the selected photo');
    };
    reader.readAsDataURL(file);
  };

  const stopRecording = () => {
    clearInterval(timer.current);
    timer.current = null;
    const currentRecorder = recorder.current;
    if (currentRecorder && currentRecorder.state !== 'inactive') {
      currentRecorder.stop();
    }
    setRecording(false);
  };

  const startRecording = async () => {
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('MediaRecorder unavailable');
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const currentRecorder = new MediaRecorder(stream);
      const chunks = [];
      currentRecorder.ondataavailable = (event) => {
        if (event.data.size) chunks.push(event.data);
      };
      currentRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: currentRecorder.mimeType || 'audio/webm' });
        const objectUrl = URL.createObjectURL(blob);
        setVoiceUrl(objectUrl);
        const reader = new FileReader();
        reader.onload = () => setVoiceDataUrl(String(reader.result || ''));
        reader.onerror = () => {
          setVoiceDataUrl(null);
          showToast('Could not prepare voice note for upload');
        };
        reader.readAsDataURL(blob);
        stream.getTracks().forEach((track) => track.stop());
      };
      currentRecorder.start();
      recorder.current = currentRecorder;
      recordingStartedAt.current = Date.now();
      setRecording(true);
      setVoiceDataUrl(null);
      setVoiceTranscript('');
      setSeconds(0);
      clearInterval(timer.current);
      timer.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - recordingStartedAt.current) / 1000);
        setSeconds(Math.min(elapsed, 5));
        if (elapsed >= 5) stopRecording();
      }, 100);
    } catch (error) {
      console.error('Microphone error:', error);
      showToast('Microphone unavailable — no voice note recorded');
    }
  };

  const analyze = async () => {
    if (!hasReportContent(writtenDescription, photo, voiceDataUrl)) {
      showToast('Add a description, photo, or voice note first.');
      return;
    }
    const hasVoice = Boolean(voiceDataUrl);
    const hasPhoto = Boolean(photo || complaint.media_url);
    setAiError('');
    setAiProgress(0);
    setScreen('analysis');

    try {
      // Reading the report is immediate; optional modalities are shown as
      // skipped in the UI instead of pretending they are being processed.
      setAiProgress(1);

      let transcript = voiceTranscript;
      if (hasVoice && !transcript) {
        setAiProgress(1);
        const voiceResponse = await fetch(`${API_BASE}/api/transcribe-audio`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ audio_data_url: voiceDataUrl }),
        });
        const voiceData = await voiceResponse.json().catch(() => ({}));
        if (!voiceResponse.ok) throw new Error(voiceData.detail || `Voice transcription failed (${voiceResponse.status})`);
        transcript = voiceData.text || '';
        setVoiceTranscript(transcript);
        setAiProgress(2);
      }

      // The backend combines vision, category, severity and routing into one
      // analysis call. Keep the actually-active modality on screen while that
      // call is running instead of showing an unrelated step.
      setAiProgress(hasPhoto ? 2 : 3);
      const response = await fetch(`${API_BASE}/api/analyze-complaint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: complaint.latitude,
          longitude: complaint.longitude,
          media_url: complaint.media_url || null,
          description: writtenDescription,
          voice_transcript: transcript || null,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Analysis failed (${response.status})`);

      setAiProgress(6);
      setComplaint((current) => ({ ...current, ...data }));
      setTimeout(() => setScreen('result'), 350);
    } catch (error) {
      console.error('Complaint analysis failed:', error);
      setAiError(error.message || 'Could not analyze the report.');
    }
  };

  const submit = async () => {
    if (!hasReportContent(writtenDescription, photo, voiceDataUrl)) {
      showToast('Add a description, photo, or voice note before submitting.');
      setScreen('review');
      return;
    }
    setScreen('submitting');
    try {
      let transcript = voiceTranscript;
      if (voiceDataUrl && !transcript) {
        const voiceResponse = await fetch(`${API_BASE}/api/transcribe-audio`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ audio_data_url: voiceDataUrl }),
        });
        const voiceData = await voiceResponse.json().catch(() => ({}));
        if (!voiceResponse.ok) throw new Error(voiceData.detail || `Voice transcription failed (${voiceResponse.status})`);
        transcript = voiceData.text || '';
        setVoiceTranscript(transcript);
      }

      const response = await fetch(`${API_BASE}/api/complaints`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: complaint.latitude,
          longitude: complaint.longitude,
          media_url: complaint.media_url || null,
          description: writtenDescription,
          voice_transcript: transcript || null,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);

      setComplaint((current) => ({ ...current, ...data }));
      rememberReportId(data.id);
      setScreen('success');
    } catch (error) {
      console.error('Complaint submission failed:', error);
      setScreen('review');
      showToast(error.message || 'Could not submit report. Please try again.');
    }
  };

  const resetReport = () => {
    clearInterval(timer.current);
    if (recorder.current?.state !== 'inactive') recorder.current?.stop();
    setComplaint({ ...EMPTY_COMPLAINT });
    setWrittenDescription('');
    setVoiceTranscript('');
    setPhoto(null);
    setVoiceUrl(null);
    setVoiceDataUrl(null);
    setRecording(false);
    setSeconds(0);
    setAiError('');
    setAiProgress(0);
    setReportResetKey((key) => key + 1);
    setScreen('report');
  };

  const nav = (nextScreen) => setScreen(nextScreen);
  const openTracking = (report) => {
    setComplaint((current) => ({ ...current, ...report }));
    setScreen('tracking');
  };

  return (
    <div className="app-shell">
      <div className="app-frame">
        {screen === 'login' && <Login nav={nav} />}
        {screen === 'register' && <Register nav={nav} />}
        {screen === 'home' && <Home nav={nav} />}
        {screen === 'report' && (
          <Report key={reportResetKey}
            canContinue={hasReportContent(writtenDescription, photo, voiceDataUrl)}
            complaint={complaint}
            setComplaint={setComplaint}
            setWrittenDescription={setWrittenDescription}
            photo={photo}
            onPhoto={handlePhoto}
            recording={recording}
            seconds={seconds}
            start={startRecording}
            stop={stopRecording}
            voiceUrl={voiceUrl}
            locationState={locationState}
            getLocation={getLocation}
            next={() => nav('evidence')}
          />
        )}
        {screen === 'evidence' && (
          <Evidence
            complaint={complaint}
            photo={photo}
            voiceUrl={voiceUrl}
            seconds={seconds}
            recording={recording}
            start={startRecording}
            stop={stopRecording}
            analyze={analyze}
          />
        )}
        {screen === 'analysis' && <Analysis progress={aiProgress} error={aiError} retry={analyze} hasVoice={Boolean(voiceDataUrl)} hasPhoto={Boolean(photo || complaint.media_url)} />}
        {screen === 'result' && <Result complaint={complaint} writtenDescription={writtenDescription} voiceTranscript={voiceTranscript} review={() => nav('review')} />}
        {screen === 'review' && <Review complaint={complaint} writtenDescription={writtenDescription} voiceTranscript={voiceTranscript} photo={photo} seconds={seconds} edit={() => nav('report')} submit={submit} />}
        {screen === 'submitting' && <Submitting />}
        {screen === 'success' && <Success complaint={complaint} track={() => nav('tracking')} home={() => nav('home')} />}
        {screen === 'tracking' && <Tracking complaint={complaint} setComplaint={setComplaint} setModal={setModal} />}
        {screen === 'reports' && <MyReports openTracking={openTracking} />}
        {screen === 'profile' && <Profile lang={lang} setLang={setLang} showToast={showToast} nav={nav} theme={theme} setTheme={setTheme} />}
        {!['login', 'register', 'analysis', 'submitting'].includes(screen) && <BottomNav screen={screen} nav={nav} reset={resetReport} />}
        {toast && <div className="toast">{toast}</div>}
        {modal === 'nearby' && <Modal close={() => setModal(null)} />}
        {modal === 'helplines' && <HelpModal close={() => setModal(null)} />}
      </div>
    </div>
  );
}

const Header = ({ title, back }) => (
  <header className="topbar">
    {back ? <button className="icon-btn" onClick={back}><Icon name="back" /></button> : <img src="/logo.png" alt="Logo" style={{ width: 34, height: 34, objectFit: 'contain' }} />}
    <div><div className="brand">CivicPulse <span>AI</span></div>{title && <div className="subhead">{title}</div>}</div>
    {!back && <button className="icon-btn" aria-label="Open Jharkhand helplines" title="Jharkhand helplines" onClick={() => window.dispatchEvent(new CustomEvent('civicpulse:open-helplines'))}><Icon name="phone" /></button>}
  </header>
);

const BottomNav = ({ screen, nav, reset }) => (
  <nav className="bottom-nav">
    <button className={screen === 'home' ? 'active' : ''} onClick={() => nav('home')}><Icon name="home" /><span>Home</span></button>
    <button className={['report', 'evidence', 'analysis', 'result', 'review'].includes(screen) ? 'active report-tab' : ''} onClick={reset}><span className="report-orb"><Icon name="plus" /></span><span>Report</span></button>
    <button className={screen === 'reports' ? 'active' : ''} onClick={() => nav('reports')}><Icon name="file" /><span>My Reports</span></button>
    <button className={screen === 'profile' ? 'active' : ''} onClick={() => nav('profile')}><Icon name="user" /><span>Profile</span></button>
  </nav>
);

const Button = ({ children, onClick, secondary = false, disabled = false, icon }) => (
  <button disabled={disabled} className={`primary-btn ${secondary ? 'secondary' : ''}`} onClick={onClick}>{children}{icon && <Icon name="arrow" size={18} />}</button>
);

const Status = ({ children }) => <span className={`status ${String(children).toLowerCase().replaceAll(' ', '-')}`}>{children}</span>;

const MapCard = ({ lat = RANCHI.latitude, lon = RANCHI.longitude }) => {
  const safeLat = Number.isFinite(Number(lat)) ? Number(lat) : RANCHI.latitude;
  const safeLon = Number.isFinite(Number(lon)) ? Number(lon) : RANCHI.longitude;
  const delta = 0.006;
  const bbox = `${safeLon - delta},${safeLat - delta},${safeLon + delta},${safeLat + delta}`;
  const src = `https://www.openstreetmap.org/export/embed.html?bbox=${encodeURIComponent(bbox)}&layer=mapnik&marker=${safeLat},${safeLon}`;
  return <div className="map real-map"><iframe title="Issue location" src={src} loading="lazy" /></div>;
};

const Stepper = ({ active }) => (
  <div className="stepper">{['Details', 'Evidence', 'AI Review', 'Submit'].map((label, index) => (
    <React.Fragment key={label}><div className={`step ${index < active ? 'done ' : ''}${index === active ? 'current' : ''}`}><span>{index < active ? '✓' : index + 1}</span>{label}</div>{index < 3 && <div className="step-line" />}</React.Fragment>
  ))}</div>
);

function Home({ nav }) {
  const [stats, setStats] = useState({ submitted: 0, resolved: 0, nearby: [] });
  useEffect(() => {
    fetch(`${API_BASE}/api/complaints`)
      .then((response) => response.json())
      .then((items) => {
        const list = Array.isArray(items) ? items : [];
        setStats({ submitted: list.length, resolved: list.filter((item) => item.status === 'Resolved').length, nearby: list.slice(0, 3) });
      })
      .catch(() => {});
  }, []);

  return <div className="page"><Header /><main>
    <section className="welcome"><p className="eyebrow">GOOD MORNING</p><h1>Help make your city <em>better.</em></h1><p className="muted">Spot a civic issue? Report it in seconds and let AI route it to the right team.</p><Button onClick={() => nav('report')} icon>Report an Issue</Button></section>
    <section className="impact"><div><b>{stats.submitted}</b><span>Reports submitted</span></div><div><b>{stats.resolved}</b><span>Issues resolved</span></div><div><b>{stats.nearby.length}</b><span>Recent reports</span></div></section>
    <section className="section-head"><h2>Recent civic issues</h2><button onClick={() => nav('reports')}>View all</button></section>
    <div className="issue-list">{stats.nearby.length ? stats.nearby.map((issue) => <Issue key={issue.id} title={issue.description || 'Civic issue'} dept={issue.assigned_department || 'Unassigned'} severity={issue.ai_severity || 'Low'} />) : <div className="detail-card"><p className="muted">No reports yet. Your first report will appear here.</p></div>}</div>
    <section className="ai-banner"><div className="ai-icon"><Icon name="spark" /></div><div><b>From report to resolution</b><p>Report → AI understands → Department assigned → Track</p></div></section>
  </main></div>;
}

const Issue = ({ title, dept, severity }) => <div className="issue-card"><div className="issue-icon"><Icon name="pin" size={18} /></div><div className="issue-copy"><b>{title}</b><span>{dept}</span></div><Status>{severity}</Status></div>;

function Report({ canContinue, complaint, setComplaint, photo, onPhoto, recording, seconds, start, stop, voiceUrl, locationState, getLocation, next, setWrittenDescription }) {
  return <div className="page"><Header title="Report an Issue" back={() => window.history.back()} /><main><Stepper active={0} /><div className="screen-title"><p className="eyebrow">STEP 1 OF 4</p><h1>What happened?</h1><p className="muted">Tell us what you noticed. Add evidence to help us act faster.</p></div><label className="field-label">Description</label><textarea value={complaint.description} onChange={(event) => { setWrittenDescription(event.target.value); setComplaint((current) => ({ ...current, description: event.target.value })); }} className="textarea" placeholder="Describe the issue..." />
    <div className="evidence-actions"><label className="evidence-btn"><input type="file" accept="image/*" capture="environment" onChange={onPhoto} /><span><Icon name="camera" />Add Photo</span></label><button className={`evidence-btn ${recording ? 'recording' : ''}`} onClick={recording ? stop : start}><Icon name="mic" /><span>{recording ? `Recording 0${seconds}s` : 'Record Voice'}</span></button></div>
    {photo && <img className="photo-preview small" src={photo} alt="Selected civic evidence" />}{voiceUrl && <div className="voice-chip"><span className="pulse-dot" /><span>Voice note</span><b>00:{String(seconds).padStart(2, '0')}</b></div>}{voiceUrl && voiceUrl !== 'demo' && <audio className="voice-player inline" controls preload="metadata" src={voiceUrl}>Your browser does not support audio playback.</audio>}
    <div className="section-head location-head"><h2>Issue location</h2><button onClick={getLocation}><Icon name="refresh" size={16} /> Refresh</button></div><div className="location-card"><div className="loc-row"><div className="loc-icon"><Icon name="pin" /></div><div><b>{locationState === 'loading' ? 'Detecting location…' : locationState === 'demo' ? 'Demo location' : 'Location captured'}</b><span>{Number(complaint.latitude).toFixed(4)}, {Number(complaint.longitude).toFixed(4)}</span></div><span className="loc-ok">✓</span></div><MapCard lat={complaint.latitude} lon={complaint.longitude} /></div><Button onClick={next} disabled={!canContinue} icon>Continue</Button><p className="privacy"><Icon name="info" size={15} /> Location is used to identify the reported issue and support routing.</p>
  </main></div>;
}

function Evidence({ complaint, photo, voiceUrl, seconds, recording, start, stop, analyze }) {
  return <div className="page"><Header title="Add Evidence" back={() => window.history.back()} /><main><Stepper active={1} /><div className="screen-title"><p className="eyebrow">STEP 2 OF 4</p><h1>Strengthen your report</h1><p className="muted">Evidence helps CivicPulse AI understand the issue with greater context.</p></div><div className="evidence-card"><div className="card-top"><b>Photo evidence</b><span className={`tag ${photo ? 'success' : ''}`}>{photo ? 'Added' : 'Optional'}</span></div>{photo ? <img className="photo-preview" src={photo} alt="Civic evidence" /> : <div className="photo-placeholder"><Icon name="camera" size={32} /><b>No photo added</b><span>You can continue with text or voice.</span></div>}</div><div className="evidence-card"><div className="card-top"><b>Voice note</b><span className="tag">{voiceUrl ? `00:${String(seconds).padStart(2, '0')}` : 'Optional'}</span></div><div className="voice-row"><button className="play-btn" onClick={recording ? stop : start}><Icon name={recording ? 'check' : 'mic'} size={18} /></button><div className="wave">{Array.from({ length: 28 }, (_, index) => <i key={index} style={{ height: `${10 + (index * 17) % 22}px` }} />)}</div><span>00:{String(seconds).padStart(2, '0')}</span></div>{voiceUrl && voiceUrl !== 'demo' && <audio className="voice-player" controls preload="metadata" src={voiceUrl}>Your browser does not support audio playback.</audio>}<small>Voice is transcribed and kept separate from the written description.</small></div><MapCard lat={complaint.latitude} lon={complaint.longitude} /><Button onClick={analyze} icon>Analyze with AI</Button></main></div>;
}

function Analysis({ progress, error, retry, hasVoice, hasPhoto }) {
  const hasVoiceInput = Boolean(hasVoice);
  const hasPhotoInput = Boolean(hasPhoto);
  const steps = [
    { label: 'Reading complaint' },
    { label: 'Converting voice to text', skipped: !hasVoiceInput },
    { label: 'Analyzing image', skipped: !hasPhotoInput },
    { label: 'Identifying category' },
    { label: 'Assessing severity' },
    { label: 'Finding responsible department' },
  ];

  if (error) return <div className="center-page"><div className="ai-ring"><Icon name="info" size={32} /></div><div className="eyebrow">CIVICPULSE AI</div><h1>Analysis needs attention</h1><p className="muted">{error}</p><Button onClick={retry}>Try analysis again</Button></div>;

  return <div className="center-page"><div className="ai-loader"><div className="ai-ring"><Icon name="spark" size={34} /></div><div className="eyebrow">CIVICPULSE AI</div><h1>Understanding your report</h1><p>{hasPhotoInput || hasVoiceInput ? 'Combining the evidence you provided with the complaint context.' : 'Understanding the complaint text and location context.'}</p></div><div className="analysis-list">{steps.map((step, index) => {
    const status = step.skipped ? 'skipped' : index < progress ? 'done' : index === progress ? 'active' : 'pending';
    return <div className={`analysis-step ${status}`} key={step.label}><span>{status === 'skipped' ? '—' : status === 'done' ? '✓' : status === 'active' ? <span className="mini-spinner" /> : index + 1}</span>{step.label}{status === 'skipped' && <b>Skipped</b>}{status === 'done' && <b>Done</b>}</div>;
  })}</div><div className="progress-track"><div style={{ width: `${Math.min(progress / 6, 1) * 100}%` }} /></div><p className="muted center">Fast-path civic reports are classified locally without unnecessary transformer inference.</p></div>;
}

function Result({ complaint, writtenDescription, voiceTranscript, review }) {
  const severity = complaint.ai_severity || 'Low';
  const category = complaint.ai_category || 'General Maintenance';
  const department = complaint.assigned_department || 'Unassigned';
  const confidence = complaint.ai_confidence_score;
  const priority = Number.isFinite(Number(complaint.priority_score)) ? Number(complaint.priority_score) : null;
  const estimate = complaint.estimated_resolution_hours;
  const title = severity === 'Critical' ? 'Critical civic issue' : severity === 'High' ? 'High-priority civic issue' : severity === 'Medium' ? 'Medium-priority civic issue' : 'Civic issue identified';
  return <div className="page"><Header title="AI Results" back={() => window.history.back()} /><main>
    <div className="result-hero"><div className="check-ring"><Icon name="spark" size={25} /></div><p className="eyebrow">ANALYSIS COMPLETE</p><h1>{title}</h1><p>AI classified the submitted context and selected a municipal department.</p></div>
    <div className="insight-card"><div className="insight-top"><span className="ai-icon mini"><Icon name="spark" size={17} /></span><div><b>CivicPulse AI decision</b><span>Voice · image · text context</span></div>{typeof confidence === 'number' && <span className="confidence">{Math.round(confidence * 100)}%</span>}</div>
      <div className="result-grid"><Info label="Category" value={category} /><Info label="Severity" value={<Status>{severity}</Status>} /><Info label="Department" value={department} /><Info label="Status" value={<Status>{complaint.status || 'Pending'}</Status>} /></div>
    </div>
    <div className="result-grid">
      {priority !== null && <div className="detail-card"><Info label="Operational priority" value={`${priority}/100`} /><p className="muted small-text">{complaint.priority_reason || 'Severity + nearby report context'}</p></div>}
      <div className="detail-card"><Info label="Projected service window" value={estimate ? `${estimate} hours` : 'Calculating'} /><p className="muted small-text">{complaint.prediction_basis || 'Prototype decision-support baseline'}</p></div>
    </div>
    <div className="detail-card"><div className="section-head"><h2>Probable contributing factor</h2>{complaint.root_cause_confidence != null && <span className="tag success">{Math.round(Number(complaint.root_cause_confidence) * 100)}% signal</span>}</div><p>{complaint.probable_root_cause || 'Not available'}</p>{(complaint.root_cause_factors || []).length > 0 && <p className="muted small-text">Signals: {(complaint.root_cause_factors || []).join(' · ')}</p>}<div className="explain"><Icon name="spark" size={16} /><span>{complaint.recommended_action || 'Inspect the reported location and assign the appropriate municipal action.'}</span></div></div>
    <div className="detail-card"><div className="section-head"><h2>Written description</h2></div><p>{writtenDescription || 'No written description provided.'}</p></div>
    {voiceTranscript && <div className="detail-card"><div className="section-head"><h2>Voice transcription</h2></div><p>{voiceTranscript}</p></div>}
    <div className="detail-card"><Info label="Location" value={`${Number(complaint.latitude).toFixed(4)}, ${Number(complaint.longitude).toFixed(4)}`} /></div>
    {Number(complaint.duplicate_count || 0) > 0 && <div className="similar"><span className="similar-icon">!</span><div><b>{complaint.duplicate_count} similar report{Number(complaint.duplicate_count) === 1 ? '' : 's'} nearby</b><p>Potential duplicates can strengthen the priority signal for the same civic issue.</p></div></div>}
    <div className="explain"><Icon name="spark" size={18} /><span>The decision-support layer combines severity, local report density, community confirmations and historical resolution patterns. It is designed as a transparent hackathon prototype.</span></div>
    <Button onClick={review} icon>Review Report</Button>
  </main></div>;
}

const Info = ({ label, value }) => <div className="info"><span>{label}</span><b>{value}</b></div>;

function Review({ complaint, writtenDescription, voiceTranscript, photo, seconds, edit, submit }) {
  return <div className="page"><Header title="Review & Submit" back={edit} /><main><Stepper active={2} /><div className="screen-title"><p className="eyebrow">STEP 3 OF 4</p><h1>Review your report</h1><p className="muted">Everything looks ready. You can edit any detail before submitting.</p></div><div className="review-card"><ReviewRow label="Written description" value={writtenDescription || 'No written description provided.'} />{voiceTranscript && <ReviewRow label="Voice transcription" value={voiceTranscript} />}<ReviewRow label="Category" value={complaint.ai_category || 'Not analyzed'} /><ReviewRow label="Severity" value={<Status>{complaint.ai_severity || 'Not analyzed'}</Status>} /><ReviewRow label="Location" value={`${Number(complaint.latitude).toFixed(4)}, ${Number(complaint.longitude).toFixed(4)}`} /><ReviewRow label="Department" value={complaint.assigned_department || 'Pending AI analysis'} /><ReviewRow label="Status" value={<Status>{complaint.status || 'Pending'}</Status>} /></div>{photo && <img className="photo-preview small" src={photo} alt="Civic evidence" />}{voiceTranscript && <div className="voice-chip"><span className="pulse-dot" /><span>Voice transcription available</span><b>00:{String(seconds).padStart(2, '0')}</b></div>}<button className="edit-link" onClick={edit}><Icon name="edit" size={16} /> Edit details</button><Button onClick={submit} disabled={!((writtenDescription || '').trim() || photo || voiceTranscript)} >Submit Report</Button><button className="draft" onClick={() => alert('Draft saving is not enabled in this prototype.')}>Save as Draft</button></main></div>;
}

const ReviewRow = ({ label, value }) => <div className="review-row"><span>{label}</span><b>{value}</b></div>;
const Submitting = () => <div className="center-page"><div className="submit-loader"><span /><span /><span /></div><h1>Submitting your report…</h1><p>Creating a trackable civic ticket.</p></div>;

function Success({ complaint, track, home }) {
  return <div className="center-page success-page"><div className="success-ring"><Icon name="check" size={38} /></div><p className="eyebrow">REPORT SUBMITTED</p><h1>Your civic issue is now on the radar.</h1><p>Your report has been sent to the responsible department. Track its status from My Reports.</p><div className="success-ticket"><span>Report ID</span><b>#{complaint.id?.slice(0, 8).toUpperCase() || 'CP-NEW'}</b><div><span>{complaint.assigned_department || 'Unassigned'}</span><Status>{complaint.status || 'Pending'}</Status></div><div><span>{complaint.ai_category || 'Category pending'}</span><Status>{complaint.ai_severity || 'Low'}</Status></div><div className="privacy-token"><span>Private tracking token</span><b>{complaint.pseudonymous_id || 'Generating…'}</b></div><p className="token-note">Use this token to reference your report without sharing personal details.</p></div><Button onClick={track} icon>Track My Report</Button><button className="text-btn" onClick={home}>Back to Home</button></div>;
}

function Tracking({ complaint, setComplaint, setModal }) {
  const [syncing, setSyncing] = useState(true);
  const [syncError, setSyncError] = useState('');
  const [statusNotice, setStatusNotice] = useState('');
  useEffect(() => {
    let cancelled = false;
    const loadLatest = async () => {
      if (!complaint?.id) return;
      const previousStatus = complaint.status || 'Pending';
      const previousUpdate = complaint.updated_at || '';
      try {
        const response = await fetch(`${API_BASE}/api/complaints/${complaint.id}`);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
        if (!cancelled) {
          if (previousStatus !== data.status) {
            setStatusNotice(`Status updated: ${previousStatus} → ${data.status}`);
            setTimeout(() => setStatusNotice(''), 3500);
          } else if (previousUpdate && previousUpdate !== data.updated_at && Array.isArray(data.progress_updates) && data.progress_updates.length) {
            setStatusNotice('A new progress update is available.');
            setTimeout(() => setStatusNotice(''), 3500);
          }
          setComplaint((current) => ({ ...current, ...data }));
          setSyncError('');
        }
      } catch (error) {
        if (!cancelled) setSyncError('Live status unavailable');
      } finally {
        if (!cancelled) setSyncing(false);
      }
    };
    loadLatest();
    const interval = setInterval(loadLatest, 5000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [complaint?.id, setComplaint]);

  const status = complaint.status || 'Pending';
  const stages = ['Report Submitted', 'AI Analysis Completed', 'Department Assigned', 'Pending', 'Acknowledged', 'In Progress', 'Resolved'];
  const stageIndex = Math.max(0, stages.indexOf(status));
  const estimate = status === 'Resolved' ? null : complaint.estimated_resolution_hours;
  const verificationKey = complaint?.id ? `civicpulse.verified.${complaint.id}` : null;
  const alreadyVerified = verificationKey ? localStorage.getItem(verificationKey) === '1' : false;

  const verify = async () => {
    if (!complaint?.id || alreadyVerified) return;
    try {
      const response = await fetch(`${API_BASE}/api/complaints/${complaint.id}/verify`, { method: 'POST' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Could not confirm this issue');
      setComplaint((current) => ({ ...current, verification_count: data.verification_count, last_verified_at: data.last_verified_at, updated_at: data.last_verified_at, priority_score: data.priority_score, priority_reason: data.priority_reason, nearby_report_count: data.nearby_report_count, duplicate_count: data.duplicate_count }));
      localStorage.setItem(verificationKey, '1');
      setStatusNotice('Your confirmation was recorded and priority was recalculated.');
      setTimeout(() => setStatusNotice(''), 3000);
    } catch (error) {
      setStatusNotice(error.message || 'Could not confirm this issue');
    }
  };

  const updates = Array.isArray(complaint.progress_updates) ? complaint.progress_updates : [];
  const visibleUpdates = updates.slice().reverse();
  return <div className="page"><Header title="Track Report" back={() => window.history.back()} /><main>
    {statusNotice && <div className="detail-card notification-banner"><b>{statusNotice}</b></div>}
    <div className="track-head"><div><p className="eyebrow">#{complaint.id?.slice(0, 8).toUpperCase() || 'CP-NEW'}</p><h1>{complaint.description || 'Civic issue report'}</h1><span className="muted">{complaint.ai_category || 'Unclassified'} · {complaint.ai_severity || 'Low'} priority</span></div><Status>{status}</Status></div>
    <div className="detail-card compact"><Info label="Location" value={`${complaint.latitude?.toFixed(4) ?? '—'}, ${complaint.longitude?.toFixed(4) ?? '—'}`} /><Info label="Assigned department" value={complaint.assigned_department || 'Unassigned'} />{complaint.resolved_at && <Info label="Resolved at" value={formatLocalTime(complaint.resolved_at)} />}<div className="token-inline"><span>Private tracking token</span><b>{complaint.pseudonymous_id || '—'}</b></div></div>
    <div className="timeline">{stages.map((stage, index) => <div className={`timeline-item ${index < stageIndex ? 'done ' : ''}${index === stageIndex ? 'current' : ''}`} key={stage}><div className="timeline-dot">{index < stageIndex ? '✓' : index === stageIndex ? '•' : ''}</div><div><b>{stage}</b>{index === stageIndex && <span>{status === 'Resolved' ? 'Issue resolved' : `Current status · ${status}`}</span>}</div></div>)}</div>
    <div className="estimate"><span className="ai-icon mini"><Icon name="clock" size={16} /></span><div><b>{status === 'Resolved' ? 'Resolution complete' : 'Projected service window'}</b><p>{status === 'Resolved' ? 'This complaint has been resolved.' : estimate ? `Estimated resolution: ${estimate} hours.` : severityWindow(complaint.ai_severity)}</p><small>{complaint.prediction_basis || 'Prototype prediction using severity and operational context.'}</small></div></div>
    {status === 'Resolved' && complaint.resolution_media_url && (
      <div className="detail-card resolution-proof-card">
        <div className="section-head"><h2>Completion evidence</h2><span className="tag success">Verified by Operations</span></div>
        <p className="muted small-text">A photo was uploaded by municipal operations to document the completed work.</p>
        <img className="resolution-proof-image" src={complaint.resolution_media_url} alt="Photo showing the completed civic issue resolution" loading="lazy" />
      </div>
    )}
    <div className="detail-card"><div className="section-head"><h2>Contributing factor</h2>{complaint.root_cause_confidence != null && <span className="tag success">{Math.round(Number(complaint.root_cause_confidence) * 100)}% signal</span>}</div><p>{complaint.probable_root_cause || 'Not available'}</p>{(complaint.root_cause_factors || []).length > 0 && <p className="muted small-text">Signals: {(complaint.root_cause_factors || []).join(' · ')}</p>}{complaint.recommended_action && <div className="explain"><Icon name="spark" size={16} /><span>{complaint.recommended_action}</span></div>}</div>
    <div className="detail-card notification-card"><div className="section-head"><h2>Progress notifications</h2><span className="tag success">Live</span></div>{visibleUpdates.length ? <div className="notification-list">{visibleUpdates.map((item, index) => <div className="notification-item" key={`${item.timestamp}-${index}`}><span className="notification-icon"><Icon name={item.kind === 'admin' || item.kind === 'assignment' ? 'message' : item.kind === 'community' ? 'check' : 'bell'} size={14} /></span><div><b>{item.message}</b><span>{formatLocalTime(item.timestamp)}</span></div></div>)}</div> : <p className="muted">No progress notifications yet.</p>}</div>
    <div className="community"><div className="avatars"><span>{Number(complaint.verification_count || 0)}</span><span>GPS</span><span>✓</span></div><div><b>Community verification</b><p>{complaint.verification_count || 0} confirmation{Number(complaint.verification_count || 0) === 1 ? '' : 's'} · priority {Number(complaint.priority_score || 0)}/100</p></div><button onClick={verify} disabled={alreadyVerified}>{alreadyVerified ? 'Confirmed' : 'Confirm'}</button></div>
    {Number(complaint.duplicate_count || 0) > 0 && <div className="similar"><span className="similar-icon">!</span><div><b>{complaint.duplicate_count} possible duplicate report{Number(complaint.duplicate_count) === 1 ? '' : 's'}</b><p>Nearby reports with similar issue context help identify recurring civic problems.</p></div></div>}
    <p className="muted center">{syncing ? 'Syncing latest status…' : syncError || 'Status and progress are synced with CivicPulse Ops'}</p>
  </main></div>;
}

const severityWindow = (severity) => ({ Critical: '24 hours', High: '48 hours', Medium: '3–5 days', Low: '5–7 days' }[severity] || 'not available');

const formatLocalTime = (value) => { const date = new Date(value); return Number.isFinite(date.getTime()) ? date.toLocaleString() : '—'; };

function MyReports({ openTracking }) {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState('All');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = async () => {
    setLoading(true); setError('');
    try {
      const ids = readStoredReportIds();
      if (!ids.length) { setItems([]); return; }
      const staleIds = [];
      const results = await Promise.all(ids.map(async (id) => {
        try {
          const response = await fetch(`${API_BASE}/api/complaints/${id}`);
          if (response.ok) return response.json();
          if (response.status === 404) staleIds.push(id);
          return null;
        } catch {
          return null;
        }
      }));
      if (staleIds.length) {
        const remainingIds = readStoredReportIds().filter((id) => !staleIds.includes(id));
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(remainingIds)); } catch {}
      }
      setItems(results.filter(Boolean));
    } catch (error) { setError(error.message || 'Could not load your reports.'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  const filtered = filter === 'All' ? items : items.filter((item) => filter === 'Resolved' ? item.status === 'Resolved' : item.status !== 'Resolved');
  const pendingCount = items.filter((item) => item.status !== 'Resolved').length;
  const resolvedCount = items.filter((item) => item.status === 'Resolved').length;
  return <div className="page"><Header title="My Reports" /><main><div className="screen-title"><p className="eyebrow">YOUR ACTIVITY</p><h1>Reports</h1><p className="muted">Keep track of every issue you’ve raised.</p></div><div className="filter-row"><button className={filter === 'All' ? 'selected' : ''} onClick={() => setFilter('All')}>All <span>{items.length}</span></button><button className={filter === 'Pending' ? 'selected' : ''} onClick={() => setFilter('Pending')}>Pending <span>{pendingCount}</span></button><button className={filter === 'Resolved' ? 'selected' : ''} onClick={() => setFilter('Resolved')}>Resolved <span>{resolvedCount}</span></button></div>{loading ? <div className="detail-card"><p className="muted">Loading your reports…</p></div> : error ? <div className="detail-card"><p>{error}</p><button className="text-btn" onClick={load}>Try again</button></div> : filtered.length === 0 ? <div className="detail-card"><h2>No reports yet</h2><p className="muted">Submit a civic issue and it will appear here automatically.</p></div> : <div className="reports-list">{filtered.map((report) => <button className="report-card" key={report.id} onClick={() => openTracking(report)}><div className="report-card-top"><span className="report-number">#{report.id.slice(0, 8).toUpperCase()}</span><Status>{report.status || 'Pending'}</Status></div><h3>{report.description || report.voice_transcript || 'Civic issue report'}</h3><p>{report.ai_category || 'Unclassified'} · {report.assigned_department || 'Unassigned'}</p><div className="report-card-foot"><span>{typeof report.latitude === 'number' ? report.latitude.toFixed(4) : '—'}, {typeof report.longitude === 'number' ? report.longitude.toFixed(4) : '—'}</span><Icon name="arrow" size={16} /></div></button>)}</div>}<button className="text-btn" onClick={load}>Refresh reports</button></main></div>;
}

function Profile({ lang, setLang, showToast, nav, theme, setTheme }) {
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    try {
      const stored = localStorage.getItem('civicpulse.user');
      if (stored) setUser(JSON.parse(stored));
    } catch (e) {}
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('civicpulse.user');
    nav('login');
  };

  const name = user?.name || 'Demo Citizen';
  const email = user?.email || 'CivicPulse member';
  const initials = name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || 'DC';

  return (
    <div className="page">
      <Header title="Profile" />
      <main>
        <div className="profile-head">
          <div className="avatar">{initials}</div>
          <div>
            <h1>{name}</h1>
            <p className="muted">{email}</p>
          </div>
        </div>
        
        <div className="setting-section" style={{ marginTop: '0' }}>
          <h3>Preferences</h3>
          <Setting title="Theme" icon="sun">
            <div className="lang-toggle">
              <button className={theme === 'light' ? 'selected' : ''} onClick={() => setTheme('light')}>Light</button>
              <button className={theme === 'dark' ? 'selected' : ''} onClick={() => setTheme('dark')}>Dark</button>
            </div>
          </Setting>
          <Setting title="Language" icon="globe">
            <div className="lang-toggle">
              <button className={lang === 'English' ? 'selected' : ''} onClick={() => setLang('English')}>EN</button>
              <button className={lang === 'Hindi' ? 'selected' : ''} onClick={() => setLang('Hindi')}>HI</button>
            </div>
          </Setting>
          <Setting title="Notifications" icon="bell"><Toggle on={true} onChange={() => showToast('Notifications are enabled for this demo')} /></Setting>
          <Setting title="Location permission" icon="pin"><span className="setting-value">Browser controlled</span></Setting>
        </div>

        <div className="setting-section">
          <h3>Accessibility</h3>
          <Setting title="Large text" icon="info"><Toggle /></Setting>
          <Setting title="High contrast" icon="spark"><Toggle /></Setting>
          <Setting title="Voice-first reporting" icon="mic"><Toggle on /></Setting>
        </div>

        <div className="setting-section">
          <h3>Privacy</h3>
          <p className="muted small-text">Data access and processing follow applicable consent, privacy and data-governance requirements.</p>
        </div>

        <div style={{ marginTop: '2rem', textAlign: 'center' }}>
          <button className="text-btn" style={{ color: '#e53e3e' }} onClick={handleLogout}>Sign Out</button>
        </div>
      </main>
    </div>
  );
}
const Setting = ({ title, icon, children }) => <div className="setting"><div className="setting-left"><span className="setting-icon"><Icon name={icon} size={17} /></span><b>{title}</b></div>{children}</div>;
const Toggle = ({ on = false, onChange }) => <button className={`toggle ${on ? 'on' : ''}`} onClick={onChange}><span /></button>;
function HelpModal({ close }) {
  const helplines = [
    { label: 'Emergency Response', number: '112', note: 'Jharkhand emergency response system', emergency: true },
    { label: 'Police', number: '100', note: 'Police assistance' },
    { label: 'Fire & Rescue', number: '102', note: 'Fire emergency' },
    { label: 'Ambulance', number: '108', note: 'Medical emergency' },
    { label: 'Blood Bank', number: '1910', note: 'Blood bank helpline' },
    { label: 'Health Helpline', number: '104', note: 'Public health support' },
    { label: 'Electricity · JBVNL', number: '1912', note: 'Electricity complaints' },
    { label: 'JBVNL Customer Care', number: '18003456570', note: 'Power utility support' },
    { label: 'Women Safety', number: '9771432103', note: 'Jharkhand Police Mahila Help Line' },
    { label: 'Child Help Line', number: '8877444444', note: 'Jharkhand Police child helpline' },
    { label: 'Cyber Crime', number: '9771432133', note: 'Jharkhand Police cyber crime' },
    { label: 'Citizen Grievance', number: '181', note: 'State grievance support' },
  ];
  return <div className="modal-backdrop" onClick={close}>
    <div className="modal helpline-modal" onClick={(event) => event.stopPropagation()}>
      <div className="modal-grab" />
      <div className="modal-head">
        <div><p className="eyebrow">JHARKHAND PUBLIC SERVICES</p><h2>Civic helplines</h2></div>
        <button className="icon-btn" onClick={close} aria-label="Close helplines">×</button>
      </div>
      <p className="muted helpline-note">Tap a number to call the relevant authority.</p>
      <div className="helpline-list">
        {helplines.map((item) => <a key={item.number + item.label} className={`helpline-item ${item.emergency ? 'emergency' : ''}`} href={`tel:${item.number}`}>
          <span className="helpline-icon"><Icon name="phone" size={16} /></span>
          <span className="helpline-copy"><b>{item.label}</b><small>{item.note}</small></span>
          <strong>{item.number}</strong>
        </a>)}
      </div>
      <Button onClick={close}>Done</Button>
    </div>
  </div>;
}

function Modal({ close }) { return <div className="modal-backdrop" onClick={close}><div className="modal" onClick={(event) => event.stopPropagation()}><div className="modal-grab" /><div className="modal-head"><div><p className="eyebrow">NEARBY INTELLIGENCE</p><h2>Related reports</h2></div><button className="icon-btn" onClick={close}>×</button></div><div className="nearby-item"><div className="mini-map"><Icon name="pin" /></div><div><b>Related report cluster</b><p>Used for hotspot and duplicate analysis</p></div></div><div className="nearby-item"><div className="mini-map"><Icon name="spark" /></div><div><b>Operational priority</b><p>Severity + nearby report density</p></div></div><Button onClick={close}>Done</Button></div></div>; }
function Login({ nav }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }
      localStorage.setItem('civicpulse.user', JSON.stringify(data));
      nav('home');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page center-page">
      <img src="/logo.png" alt="CivicPulse AI" style={{ width: '140px', marginBottom: '2rem', filter: 'drop-shadow(0 8px 16px rgba(0,0,0,0.1))' }} />
      
      <form onSubmit={handleLogin} style={{ width: '100%', maxWidth: 320, textAlign: 'left' }}>
        {error && <div style={{ color: 'red', marginBottom: '1rem', fontSize: '14px' }}>{error}</div>}
        <div style={{ marginBottom: '1rem' }}>
          <label className="field-label">Email</label>
          <input 
            type="email" 
            className="textarea" 
            style={{ minHeight: 'auto', padding: '12px' }} 
            placeholder="citizen@example.com" 
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />
        </div>
        <div style={{ marginBottom: '1.5rem' }}>
          <label className="field-label">Password</label>
          <input 
            type="password" 
            className="textarea" 
            style={{ minHeight: 'auto', padding: '12px' }} 
            placeholder="••••••••" 
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />
        </div>
        <Button type="submit" disabled={!email || !password || loading}>
          {loading ? 'Signing In...' : 'Sign In'}
        </Button>
      </form>
      
      <p style={{ marginTop: '2rem' }} className="muted">
        Don't have an account? <button type="button" className="text-btn" onClick={() => nav('register')} style={{ display: 'inline', padding: 0 }}>Register</button>
      </p>
    </div>
  );
}

function Register({ nav }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Registration failed');
      }
      nav('login');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page center-page">
      <img src="/logo.png" alt="CivicPulse AI" style={{ width: '140px', marginBottom: '2rem', filter: 'drop-shadow(0 8px 16px rgba(0,0,0,0.1))' }} />
      
      <form onSubmit={handleRegister} style={{ width: '100%', maxWidth: 320, textAlign: 'left' }}>
        {error && <div style={{ color: 'red', marginBottom: '1rem', fontSize: '14px' }}>{error}</div>}
        <div style={{ marginBottom: '1rem' }}>
          <label className="field-label">Full Name</label>
          <input 
            type="text" 
            className="textarea" 
            style={{ minHeight: 'auto', padding: '12px' }} 
            placeholder="Demo Citizen" 
            value={name}
            onChange={e => setName(e.target.value)}
            required
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label className="field-label">Email</label>
          <input 
            type="email" 
            className="textarea" 
            style={{ minHeight: 'auto', padding: '12px' }} 
            placeholder="citizen@example.com" 
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />
        </div>
        <div style={{ marginBottom: '1.5rem' }}>
          <label className="field-label">Password</label>
          <input 
            type="password" 
            className="textarea" 
            style={{ minHeight: 'auto', padding: '12px' }} 
            placeholder="••••••••" 
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />
        </div>
        <Button type="submit" disabled={!name || !email || !password || loading}>
          {loading ? 'Creating Account...' : 'Create Account'}
        </Button>
      </form>
      
      <p style={{ marginTop: '2rem' }} className="muted">
        Already have an account? <button type="button" className="text-btn" onClick={() => nav('login')} style={{ display: 'inline', padding: 0 }}>Sign In</button>
      </p>
    </div>
  );
}

export default App;
