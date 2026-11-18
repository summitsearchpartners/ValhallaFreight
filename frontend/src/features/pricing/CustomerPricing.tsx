import {Link} from 'react-router-dom';
import {Card,PageHead} from '../../components/UI';
export default function CustomerPricing(){
 return <><PageHead eyebrow="YOUR SHIPPING PRICES" title="Shipment pricing" sub="Compare the prices available for your freight."/><Card><h3>Get a price for your shipment</h3><p>Enter your lane and freight details in Quote Studio to compare carrier options and select your preferred service.</p><Link className="btn primary" to="/quotes">Open Quote Studio</Link></Card></>;
}
