import { useState, useEffect } from 'react';
import './App.css'
import Plot from './components/Plot'

function App() {

  const [response, setResponse] = useState<string>('');

  useEffect(() => {
    const fetchPlot = async () => {
      const response = await fetch(`/api`, );
      const j = await response.json();
      console.log(j);
      setResponse(j.message);
    };

    fetchPlot();
  }, []);

  return (
    <>
      <h1>Vite + React</h1>
      <div><h3> hello response:</h3>
        <p>{response}</p>
      </div>
      <Plot />
    </>
  )
}

export default App
