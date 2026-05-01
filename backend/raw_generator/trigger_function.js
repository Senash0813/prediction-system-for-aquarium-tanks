exports = async function(changeEvent) {
  const mongodb = context.services.get("aquaGaurd1");

  if (!mongodb) {
    throw new Error(
      "Linked data source 'aquaGaurd1' not found. Check App Services -> Linked Data Sources."
    );
  }

  const db = mongodb.db("aqua_gaurd_db");

  const rawDoc = changeEvent.fullDocument;
  if (!rawDoc) {
    console.log("No fullDocument found. Exiting.");
    return;
  }

  const rawCollectionName = changeEvent.ns.coll;

  // Only process collections like raw_tank_01, raw_tank_06, raw_tank_1, etc.
  if (!rawCollectionName.startsWith("raw_tank_")) {
    console.log(`Skipping unsupported collection: ${rawCollectionName}`);
    return;
  }

  const suffix = rawCollectionName.replace("raw_tank_", "");
  const targetCollectionName = `tank_${suffix}`;
  const tankId = `tank_${suffix}`;

  const rawCollection = db.collection(rawCollectionName);
  const targetCollection = db.collection(targetCollectionName);
  const stateCollection = db.collection("tank_state");

  const DEFAULTS = {
    temperature: 25.5,
    ph: 7.2,
    turbidity: 2.5,
    tds: 290.0,
    light: 150.0
  };

  function getNumberOrNull(value) {
    return typeof value === "number" && !isNaN(value) ? value : null;
  }

  function categorizeLight(lux) {
    if (lux == null) return null;
    if (lux < 50) return "Night Mode";
    if (lux < 500) return "Dim Light";
    if (lux < 2000) return "Low Light";
    if (lux < 5000) return "Ideal for Fish";
    if (lux < 10000) return "Great for Plants";
    return "Too Bright";
  }

  function cleanSensorData(data, lastGoodValues) {
    let temp = getNumberOrNull(data.temperature);
    let ph = getNumberOrNull(data.ph);
    let turbidity = getNumberOrNull(data.turbidity);
    let tds = getNumberOrNull(data.tds);
    let light = getNumberOrNull(data.light);

    if (temp === null || temp < 0 || temp > 40) {
      temp = lastGoodValues.temperature ?? DEFAULTS.temperature;
    }

    if (ph === null || ph < 0 || ph > 14) {
      ph = lastGoodValues.ph ?? DEFAULTS.ph;
    }

    if (turbidity === null || turbidity < 0) {
      turbidity = lastGoodValues.turbidity ?? DEFAULTS.turbidity;
    }

    if (tds === null || tds < 0 || tds > 2000) {
      tds = lastGoodValues.tds ?? DEFAULTS.tds;
    }

    if (light === null || light < 0) {
      light = lastGoodValues.light ?? DEFAULTS.light;
    }

    data.temperature = temp;
    data.ph = ph;
    data.turbidity = turbidity;
    data.tds = tds;
    data.light = light;

    return {
      cleaned: data,
      newLastGoodValues: {
        temperature: temp,
        ph: ph,
        turbidity: turbidity,
        tds: tds,
        light: light
      }
    };
  }

  function transformSensorData(data, samplingIntervalMinutes) {
    data.ingestion_time = new Date();
    data.sampling_interval = samplingIntervalMinutes;
    data.light = categorizeLight(data.light);
    return data;
  }

  try {
    const stateDoc = await stateCollection.findOne({ _id: tankId });
    const lastGoodValues = stateDoc?.last_good_values || DEFAULTS;

    const workingDoc = { ...rawDoc };
    delete workingDoc.processed;
    delete workingDoc.processed_at;

    if (typeof workingDoc.tank_id !== "string" || !workingDoc.tank_id) {
      workingDoc.tank_id = tankId;
    }

    const { cleaned, newLastGoodValues } = cleanSensorData(workingDoc, lastGoodValues);
    const finalDoc = transformSensorData(cleaned, 3);

    finalDoc._id = rawDoc._id;
    finalDoc.tank_id = tankId;

    await targetCollection.replaceOne(
      { _id: rawDoc._id },
      finalDoc,
      { upsert: true }
    );

    await rawCollection.updateOne(
      { _id: rawDoc._id },
      {
        $set: {
          processed: true,
          processed_at: new Date()
        }
      }
    );

    await stateCollection.updateOne(
      { _id: tankId },
      {
        $set: {
          last_good_values: newLastGoodValues,
          updated_at: new Date()
        }
      },
      { upsert: true }
    );

    console.log(`Processed ${rawCollectionName} -> ${targetCollectionName} for _id=${rawDoc._id}`);
  } catch (error) {
    console.log("Trigger execution failed:", error);
    throw error;
  }
};