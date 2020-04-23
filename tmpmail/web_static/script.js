(function () {
	// use non-tls websocket connection to the host for looback/localhost,
	// otherwise always use the exected public-facing websocket endpoint.
	let ws_location = undefined;
	const hostname = window.location.hostname;
	// TODO: a bit slapdash to not check for any 127.0.0.0/8
	if (hostname === 'localhost' || hostname === '127.0.0.1') {
		ws_location = `ws://${window.location.host}/inbox`;
	} else {
		ws_location = 'wss://tmpmail.oefd.ca/inbox';
	}
	const sock = new WebSocket(ws_location);

	let addr = undefined;
	const nav = document.getElementsByTagName('nav')[0];
	sock.addEventListener('message', function (event) {
		let msg = undefined;
		try {
			msg = JSON.parse(event.data);
		} catch (e) {
			console.error(`malformed message: ${e.message}`);
			return;
		}

		if (addr === undefined) {
			// set addr on first message
			if (msg.type !== 'addr') {
				console.error('protocol violation: did not get `addr` message');
				return;
			}
			addr = msg.addr;
			nav.innerText = addr;
		} else {
			// add message on subsequent messages to the first
			append_message(msg);
		}
	});
	sock.addEventListener('open', function (_event) {
		// on open send message to synchronize and get address
		sock.send('synchronize');
	});
	sock.addEventListener('close', function (_event) {
		nav.innerText = 'websocket disconnected'
	});

	function append_message(msg) {
		const main = document.getElementsByTagName('main')[0];
		if (msg.type !== 'message') {
			console.log('protocol violation: did not get `message` message');
			return;
		}

		const new_msg = document.createElement('div');
		const subject = document.createElement('h3');
		subject.innerText = `Subject: ${msg.subject}`;
		const froms = document.createElement('p');
		froms.innerText = `From: ${msg.froms.join(', ')}`;
		const tos = document.createElement('p');
		tos.innerText = `To: ${msg.tos.join(', ')}`;
		const payload = document.createElement('p');
		payload.innerText = msg.payload;

		// stitch together elements and prepend to <main>
		for (const elem of [subject, froms, tos, payload]) {
			new_msg.appendChild(elem);
		}
		main.prepend(new_msg);
	}
}());
