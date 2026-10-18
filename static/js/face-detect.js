/* ═══════════════════════════════════════════════════════════════════
   MemoAI — client-side face detection (face-api.js)
   Computes 128-d descriptors in the browser; nothing is uploaded until
   the form is submitted. Exposes window.MemoFace.
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var WEIGHTS = (window.MEMO_FACE_WEIGHTS || '/static/vendor/face-api/weights').replace(/\/$/, '');
  var readyPromise = null;

  function ready() {
    if (readyPromise) return readyPromise;
    readyPromise = new Promise(function (resolve, reject) {
      if (!window.faceapi) {
        reject(new Error('face-api.js not loaded'));
        return;
      }
      var fa = window.faceapi;
      Promise.all([
        fa.nets.tinyFaceDetector.loadFromUri(WEIGHTS),
        fa.nets.faceLandmark68Net.loadFromUri(WEIGHTS),
        fa.nets.faceRecognitionNet.loadFromUri(WEIGHTS)
      ]).then(function () { resolve(fa); }).catch(reject);
    });
    return readyPromise;
  }

  function loadImage(file) {
    return new Promise(function (resolve, reject) {
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () { resolve({ img: img, url: url }); };
      img.onerror = function () { URL.revokeObjectURL(url); reject(new Error('image load failed')); };
      img.src = url;
    });
  }

  function detectFromFile(file) {
    return ready().then(function (fa) {
      return loadImage(file).then(function (res) {
        return fa
          .detectAllFaces(res.img, new fa.TinyFaceDetectorOptions({ inputSize: 416, scoreThreshold: 0.5 }))
          .withFaceLandmarks()
          .withFaceDescriptors()
          .then(function (results) {
            URL.revokeObjectURL(res.url);
            return {
              descriptors: results.map(function (r) { return Array.prototype.slice.call(r.descriptor); }),
              boxes: results.map(function (r) {
                var b = r.detection.box;
                return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) };
              })
            };
          });
      });
    });
  }

  window.MemoFace = {
    ready: ready,
    detectFromFile: detectFromFile,
    weights: WEIGHTS
  };
})();
