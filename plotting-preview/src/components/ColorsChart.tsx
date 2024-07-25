import { useEffect, useRef, useState } from 'react';
import { Layer, Rect, Stage } from 'react-konva';

type Colors = 'r' | 'g' | 'b' | 't';

type ColorEvent = {
    c: Colors,
    i: number
}

const intensityClosure = (name: Colors) => {
    let getHex = (intensity: number) => "#000000";
    switch (name) {
        case 'r':
            getHex = (intensity: number) => `#${intensity.toString(16).padStart(2, '0')}0000`;
            break;
        case 'g':
            getHex = (intensity: number) => `#00${intensity.toString(16).padStart(2, '0')}00`;
            break;
        case 'b':
            getHex = (intensity: number) => `#0000${intensity.toString(16).padStart(2, '0')}`;
            break;
        case 't':
            getHex = (intensity: number) => {
                const hexIntensity = intensity.toString(16).padStart(2, '0');
                return `#${hexIntensity}${hexIntensity}${hexIntensity}`;
            }
            break;
        default:
            getHex = (intensity: number) => "#000000";
            break;
    }
    return getHex;
};


interface OneColorCanvasProps {
    name: Colors,
}

export function OneColorCanvas({ name }: OneColorCanvasProps) {
    const [data, setData] = useState<number[]>([]);
    const ws = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Establish WebSocket connection
        ws.current = new WebSocket('/ws/colors');
        console.log(ws.current);
        ws.current.onmessage = (event) => {
            const parsedData: ColorEvent = JSON.parse(event.data);
            if (parsedData.c == name) {
                setData(prevData => {
                    const newData = [...prevData, parsedData.i];
                    return newData
                });
            }
        };

        // Cleanup WebSocket connection on component unmount
        return () => {
            if (ws.current) {
                ws.current.close();
            }
        };
    }, []);
    const getHex = intensityClosure(name);

    return (
        <div id={name}>
            <div>On color {name} stuffs</div>
            <Stage width={window.innerWidth} height={window.innerHeight}>
                <Layer>
                    {data.map((intensity, index) => {
                        const color = getHex(intensity);
                        <Rect
                            key={index}
                            x={20 + (index % 10) * 60} // Example layout
                            y={20 + Math.floor(index / 10) * 60}
                            width={50}
                            height={50}
                            fill={color}
                            shadowBlur={5}
                        />
                    })}
                </Layer>
            </Stage>
        </div>
    )
}



function ColorsChart() {
    return (
        <div className="websocketed">
            <h3>Colors Data</h3>
            <OneColorCanvas name={'r'} />
            <OneColorCanvas name={'g'} />
            <OneColorCanvas name={'b'} />
            <OneColorCanvas name={'t'} />
        </div>
    );
}

export default ColorsChart;
